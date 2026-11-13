#!/usr/bin/env python3
"""Abstract base class for Cloudflare service sections."""

from abc import ABC, abstractmethod
from typing import Any

from .cache import APICounter
from .client import CloudflareClient
from .constants import ERROR_CATEGORY_DISCOVERY
from .logger import LoggerMixin
from .types import MetricDefinition, MetricResult, Resource


class CloudflareSection(ABC, LoggerMixin):
    """Abstract base class for Cloudflare service sections.

    Each section represents a Cloudflare service (Workers, KV, Zones, etc.)
    and implements resource discovery and metric fetching.
    """

    def __init__(
        self,
        client: CloudflareClient,
        api_counter: APICounter,
    ) -> None:
        """Initialize section.

        Args:
            client: Cloudflare API client
            api_counter: API request counter
        """
        self.client = client
        self.api_counter = api_counter

    @property
    @abstractmethod
    def name(self) -> str:
        """Service identifier (e.g., 'workers', 'kv', 'zones').

        Returns:
            Service name used as key in output
        """

    @property
    @abstractmethod
    def resource_type(self) -> str:
        """Resource type for identification.

        Returns:
            Type string (e.g., 'worker', 'kv_namespace', 'zone')
        """

    @property
    @abstractmethod
    def metrics(self) -> list[MetricDefinition]:
        """List of metrics to fetch for this service.

        Returns:
            List of metric definitions
        """

    @abstractmethod
    def discover_resources(self) -> list[Resource]:
        """Discover resources for this service.

        Returns:
            List of discovered resources
        """

    @abstractmethod
    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch analytics/metrics for discovered resources.

        Args:
            resources: List of resources to fetch metrics for
            timeframe: Time range for analytics (e.g., '24h')

        Returns:
            List of metric results
        """

    def _discover_zones(self, include_plan: bool = False) -> list[Resource]:
        """Common zone discovery for zone-based services.

        Args:
            include_plan: Whether to include plan name in metadata

        Returns:
            List of zone resources
        """
        zones = self.client.list_zones()
        resources = []

        for zone in zones:
            zone_id = zone.get("id")
            if not zone_id:
                continue

            metadata: dict[str, Any] = {
                "name": zone.get("name"),
                "status": zone.get("status"),
            }
            if include_plan:
                metadata["plan"] = zone.get("plan", {}).get("name")

            resources.append(
                Resource(
                    id=zone_id,
                    name=zone.get("name", zone_id),
                    resource_type=self.resource_type,
                    metadata=metadata,
                    available_metrics=[m.name for m in self.metrics],
                )
            )

        return resources

    def run(self, timeframe: str = "24h") -> dict[str, Any]:
        """Run the section: discover resources and fetch metrics.

        Args:
            timeframe: Time range for analytics

        Returns:
            Dictionary with resources and metrics data
        """
        self.log_info(f"Running section: {self.name}")

        # Phase 1: Discover resources
        try:
            resources = self.discover_resources()
            self.log_info(f"Discovered {len(resources)} {self.resource_type}(s)")
        except Exception as exc:
            self.log_error(f"Discovery failed for {self.name}: {exc}")
            # Report it and mark it temporary, so the empty list is not cached as the
            # discovery result and the last good data is served
            self.client.error_collector.add(
                ERROR_CATEGORY_DISCOVERY,
                self.name,
                f"Discovery failed: {exc}",
                transient=True,
            )
            resources = []

        # Phase 2: Fetch analytics
        try:
            metrics = self.fetch_analytics(resources, timeframe)
            self.log_info(f"Fetched {len(metrics)} metrics for {self.name}")
        except Exception as exc:
            self.log_error(f"Analytics fetch failed for {self.name}: {exc}")
            metrics = []

        return {
            "resources": [r.to_dict() for r in resources],
            "metrics": [m.to_dict() for m in metrics],
            "timeframe": timeframe,
        }

    def __repr__(self) -> str:
        """Return a debug representation of the section.

        Returns:
            str: Class and service name representation.
        """
        return f"<{self.__class__.__name__}(name={self.name})>"
