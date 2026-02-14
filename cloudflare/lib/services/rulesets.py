#!/usr/bin/env python3
"""Rulesets section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric

# Ruleset phases we monitor (replacing Page Rules functionality)
MONITORED_PHASES = {
    "http_request_redirect": "redirect",
    "http_request_dynamic_redirect": "redirect",
    "http_request_cache_settings": "cache",
    "http_config_settings": "config",
    "http_request_origin": "origin",
}


class RulesetsSection(CloudflareSection):
    """Section for Cloudflare Rulesets monitoring.

    Monitors zone rulesets including:
    - Total ruleset count
    - Rules by type (redirect, cache, config, origin)
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "rulesets"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for zone ruleset items.
        """
        return "zone"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for ruleset checks.
        """
        return [
            MetricDefinition("ruleset_count", "gauge", "Count"),
            MetricDefinition("redirect_rules", "gauge", "Count"),
            MetricDefinition("cache_rules", "gauge", "Count"),
            MetricDefinition("config_rules", "gauge", "Count"),
            MetricDefinition("origin_rules", "gauge", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all DNS zones for rulesets monitoring."""
        return self._discover_zones()

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch rulesets metrics.

        Args:
            resources: List of zone resources
            timeframe: Time range (not used for status)

        Returns:
            List of metric results
        """
        results: list[MetricResult] = []

        for resource in resources:
            rulesets = self.client.list_zone_rulesets(resource.id)

            # Count rulesets by phase type
            counts = {
                "redirect": 0,
                "cache": 0,
                "config": 0,
                "origin": 0,
            }

            for ruleset in rulesets:
                phase = ruleset.get("phase", "")
                if phase in MONITORED_PHASES:
                    rule_type = MONITORED_PHASES[phase]
                    counts[rule_type] += 1

            # Total rulesets (only the monitored ones)
            total_rulesets = sum(counts.values())

            results.append(
                create_metric(
                    resource, "ruleset_count", float(total_rulesets), "Count", "gauge", timeframe
                )
            )
            results.append(
                create_metric(
                    resource,
                    "redirect_rules",
                    float(counts["redirect"]),
                    "Count",
                    "gauge",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource, "cache_rules", float(counts["cache"]), "Count", "gauge", timeframe
                )
            )
            results.append(
                create_metric(
                    resource, "config_rules", float(counts["config"]), "Count", "gauge", timeframe
                )
            )
            results.append(
                create_metric(
                    resource, "origin_rules", float(counts["origin"]), "Count", "gauge", timeframe
                )
            )

        return results
