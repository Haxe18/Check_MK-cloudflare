#!/usr/bin/env python3
"""WAF section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class WAFSection(CloudflareSection):
    """Section for Cloudflare WAF/Security Events monitoring.

    Monitors security events per zone including:
    - Total events
    - Blocked requests
    - Challenged requests
    """

    def __init__(self, *args, **kwargs):
        """Initialize WAF section and skipped-zones tracking."""
        super().__init__(*args, **kwargs)
        self._skipped_free_zones: list[str] = []

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "waf"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for WAF zone items.
        """
        return "zone"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for WAF checks.
        """
        return [
            MetricDefinition("total_events", "sum", "Count"),
            MetricDefinition("blocked_events", "sum", "Count"),
            MetricDefinition("challenged_events", "sum", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all DNS zones for WAF monitoring."""
        return self._discover_zones(include_plan=True)

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch WAF security events via GraphQL.

        Args:
            resources: List of zone resources
            timeframe: Time range for analytics

        Returns:
            List of metric results
        """
        if not resources:
            return []

        zone_ids = [r.id for r in resources]
        zone_plans = {r.id: r.metadata.get("plan", "Free") for r in resources}
        zone_names = {r.id: r.name for r in resources}
        analytics, skipped_zones = self.client.fetch_waf_analytics(
            zone_ids, zone_plans, zone_names, timeframe
        )
        # Store skipped zones for orchestrator to collect
        self._skipped_free_zones = skipped_zones
        results = []

        for resource in resources:
            zone_data = analytics.get(resource.id, {})

            total_events = float(zone_data.get("total", 0))
            blocked_events = float(zone_data.get("blocked", 0))
            challenged_events = float(zone_data.get("challenged", 0))

            results.append(
                create_metric(resource, "total_events", total_events, "Count", "sum", timeframe)
            )
            results.append(
                create_metric(resource, "blocked_events", blocked_events, "Count", "sum", timeframe)
            )
            results.append(
                create_metric(
                    resource,
                    "challenged_events",
                    challenged_events,
                    "Count",
                    "sum",
                    timeframe,
                )
            )

        return results
