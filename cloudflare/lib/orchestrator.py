#!/usr/bin/env python3
"""Main orchestrator for Cloudflare monitoring."""

import time
from typing import Any

from .base import CloudflareSection
from .cache import APICounter, DataCache, get_cache_dir
from .client import CloudflareClient
from .constants import (
    CACHE_PREFIX_DISCOVERY,
    CACHE_PREFIX_METRICS,
    DEFAULT_CACHE_TTL,
    DEFAULT_DISCOVERY_TTL,
    DEFAULT_TIMEFRAME,
    ERROR_CATEGORY_API,
    ERROR_CATEGORY_DISCOVERY,
    ERROR_CATEGORY_METRICS,
)
from .logger import LoggerMixin
from .services import SECTION_REGISTRY
from .types import Resource


class CloudflareOrchestrator(LoggerMixin):
    """Coordinates running all Cloudflare sections.

    The orchestrator manages:
    - API client initialization
    - Caching (discovery and metrics with different TTLs)
    - Service section execution
    - Result aggregation
    """

    def __init__(
        self,
        api_token: str,
        account_id: str,
        services: list[str],
        cache_ttl: int = DEFAULT_CACHE_TTL,
        discovery_ttl: int = DEFAULT_DISCOVERY_TTL,
        timeframe: str = DEFAULT_TIMEFRAME,
    ) -> None:
        """Initialize orchestrator.

        Args:
            api_token: Cloudflare API token
            account_id: Cloudflare account ID
            services: List of service names to run
            cache_ttl: Metrics cache TTL in seconds
            discovery_ttl: Discovery cache TTL in seconds
            timeframe: Analytics timeframe (e.g., '24h')
        """
        self.api_token = api_token
        self.account_id = account_id
        self.services = services
        self.cache_ttl = cache_ttl
        self.discovery_ttl = discovery_ttl
        self.timeframe = timeframe

        # Initialize components
        self.api_counter = APICounter()
        self.client = CloudflareClient(
            api_token=api_token,
            account_id=account_id,
            api_counter=self.api_counter,
        )

        # Set up caches
        cache_dir = get_cache_dir(account_id)
        self.discovery_cache = DataCache(
            cache_dir=cache_dir,
            ttl=discovery_ttl,
            prefix=CACHE_PREFIX_DISCOVERY,
        )
        self.metrics_cache = DataCache(
            cache_dir=cache_dir,
            ttl=cache_ttl,
            prefix=CACHE_PREFIX_METRICS,
        )

    @property
    def _config_key(self) -> str:
        """Get config key for cache validation.

        Returns a string that changes when configuration changes,
        causing cache invalidation on config changes.
        """
        return ",".join(sorted(self.services))

    def _run_section(self, section_class: type[CloudflareSection]) -> dict[str, Any]:
        """Run a single section with caching.

        Args:
            section_class: Section class to instantiate and run

        Returns:
            Section result data
        """
        section = section_class(self.client, self.api_counter)
        service_name = section.name
        cache_key = f"{service_name}_{self.timeframe}"
        config_key = self._config_key

        # Try to load from metrics cache first (invalidates on config change)
        cached_data = self.metrics_cache.load(cache_key, config_key=config_key)
        if cached_data is not None:
            self.log_info(f"Using cached data for {service_name}")
            return cached_data

        # Check discovery cache for resources (also invalidates on config change)
        cached_resources = self.discovery_cache.load(
            f"{service_name}_resources", config_key=config_key
        )

        if cached_resources is not None:
            self.log_info(f"Using cached discovery for {service_name}")
            resources = [Resource.from_dict(r) for r in cached_resources]

            try:
                metrics = section.fetch_analytics(resources, self.timeframe)
                result = {
                    "resources": cached_resources,
                    "metrics": [m.to_dict() for m in metrics],
                    "timeframe": self.timeframe,
                }
            except Exception as exc:
                self.log_error(f"Analytics fetch failed for {service_name}: {exc}")
                result = {
                    "resources": cached_resources,
                    "metrics": [],
                    "timeframe": self.timeframe,
                    "error": str(exc),
                }
        else:
            # Full run: discovery + analytics
            result = section.run(self.timeframe)

            # Cache discovery results separately (longer TTL)
            self.discovery_cache.save(
                f"{service_name}_resources",
                result.get("resources", []),
                config_key=config_key,
            )

        # Collect errors from this section's API calls and include in result
        # This ensures errors are cached along with the metrics
        section_errors = self.client.get_and_clear_errors()
        if section_errors:
            result["section_errors"] = section_errors

        # Collect skipped Pro+ features info (e.g., WAF for Free zones)
        skipped_free_zones = getattr(section, "_skipped_free_zones", None)
        if skipped_free_zones:
            result["skipped_free_zones"] = skipped_free_zones

        # Cache full metrics result (shorter TTL)
        self.metrics_cache.save(cache_key, result, config_key=config_key)

        return result

    def run(self) -> dict[str, Any]:
        """Run all configured sections and return combined output.

        Returns:
            Dictionary with structure:
            {
                "CloudflareMetrics": { service_name: [...], ... },
                "CloudflareAPICounter": { ... },
                "CloudflareConfig": { ... }
            }
        """
        self.log_info(f"Starting Cloudflare monitoring for {len(self.services)} services")

        registry = SECTION_REGISTRY
        metrics_data: dict[str, Any] = {}
        errors: list[dict[str, str | float]] = []
        skipped_pro_features: dict[str, list[str]] = {}  # service -> [zone_names]

        for service_name in self.services:
            if service_name not in registry:
                self.log_warning(f"Unknown service: {service_name}")
                errors.append(
                    {
                        "category": ERROR_CATEGORY_DISCOVERY,
                        "service": service_name,
                        "message": f"Unknown service: {service_name}",
                        "timestamp": time.time(),
                    }
                )
                continue

            try:
                section_class = registry[service_name]
                result = self._run_section(section_class)
                metrics_data[service_name] = result
            except Exception as exc:
                self.log_error(f"Failed to run section {service_name}: {exc}")
                errors.append(
                    {
                        "category": ERROR_CATEGORY_METRICS,
                        "service": service_name,
                        "message": f"{service_name}: {str(exc)}",
                        "timestamp": time.time(),
                    }
                )
                metrics_data[service_name] = {
                    "resources": [],
                    "metrics": [],
                    "timeframe": self.timeframe,
                    "error": str(exc),
                }

        # Collect any remaining errors from the client (GraphQL errors, etc.)
        client_errors = self.client.get_and_clear_errors()
        errors.extend(client_errors)

        # Collect cached section errors from results (important for cache hits)
        # Also track services with no resources (unused permissions)
        empty_services: list[str] = []
        for service_name, result in metrics_data.items():
            section_errors = result.get("section_errors", [])
            errors.extend(section_errors)
            # Collect skipped Pro+ features info
            skipped_zones = result.get("skipped_free_zones", [])
            if skipped_zones:
                skipped_pro_features[service_name] = skipped_zones
            # Track services with no resources
            resources = result.get("resources", [])

            # Check if any API errors occurred for this service
            has_api_errors = any(
                e.get("category") == ERROR_CATEGORY_API for e in result.get("section_errors", [])
            )

            if not resources and not result.get("error") and not has_api_errors:
                empty_services.append(service_name)

        # Map empty services to their required permissions
        unused_permissions: dict[str, str] = {}
        for service_name in empty_services:
            permission = CloudflareClient.SERVICE_PERMISSIONS.get(service_name)
            if permission:
                unused_permissions[service_name] = permission

        # Build final output
        output: dict[str, Any] = {
            "CloudflareMetrics": metrics_data,
            "CloudflareAPICounter": {
                "requests_made": self.api_counter.get_count(),
                "requests_by_type": self.api_counter.get_all_counts(),
                "elapsed_seconds": self.api_counter.get_elapsed_time(),
            },
            "CloudflareConfig": {
                "services": self.services,
                "services_count": len(self.services),
                "cache_ttl": self.cache_ttl,
                "discovery_ttl": self.discovery_ttl,
                "timeframe": self.timeframe,
            },
        }

        if errors:
            output["CloudflareErrors"] = errors

        if skipped_pro_features:
            output["CloudflareSkippedProFeatures"] = skipped_pro_features

        if unused_permissions:
            output["CloudflareUnusedPermissions"] = unused_permissions

        self.log_info(
            f"Completed monitoring: {len(metrics_data)} services, "
            f"{self.api_counter.get_count()} API calls"
        )

        return output
