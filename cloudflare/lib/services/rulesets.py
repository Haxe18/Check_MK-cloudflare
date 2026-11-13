#!/usr/bin/env python3
"""Rulesets section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..parallel import parallel_map
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
    - Number of monitored rulesets
    - Number of rules by type (redirect, cache, config, origin)
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

        def count_zone_rules(zone_id: str) -> tuple[int, dict[str, int]]:
            """Count the monitored rulesets of a zone and their rules by type."""
            ruleset_count = 0
            rule_counts = {
                "redirect": 0,
                "cache": 0,
                "config": 0,
                "origin": 0,
            }

            for ruleset in self.client.list_zone_rulesets(zone_id):
                rule_type = MONITORED_PHASES.get(ruleset.get("phase", ""))
                ruleset_id = ruleset.get("id")
                if not rule_type or not ruleset_id:
                    continue

                # The ruleset list has no rules, so each monitored ruleset is read on its own
                ruleset_count += 1
                rules = self.client.get_zone_ruleset(zone_id, ruleset_id).get("rules") or []
                rule_counts[rule_type] += len(rules)

            return ruleset_count, rule_counts

        zone_counts = parallel_map(
            count_zone_rules, [resource.id for resource in resources], logger=self
        )

        results: list[MetricResult] = []

        for resource in resources:
            total_rulesets, counts = zone_counts.get(resource.id) or (
                0,
                {"redirect": 0, "cache": 0, "config": 0, "origin": 0},
            )

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
