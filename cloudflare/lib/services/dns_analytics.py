#!/usr/bin/env python3
"""DNS Analytics section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class DNSAnalyticsSection(CloudflareSection):
    """Section for Cloudflare DNS Analytics monitoring.

    Monitors DNS query analytics per zone including:
    - Query count
    - Response codes (NOERROR, NXDOMAIN, SERVFAIL)
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "dns_analytics"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for DNS analytics items.
        """
        return "zone"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for DNS analytics.
        """
        return [
            MetricDefinition("query_count", "sum", "Count"),
            MetricDefinition("noerror_count", "sum", "Count"),
            MetricDefinition("nxdomain_count", "sum", "Count"),
            MetricDefinition("servfail_count", "sum", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all DNS zones for DNS analytics."""
        return self._discover_zones()

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch DNS analytics.

        Args:
            resources: List of zone resources
            timeframe: Time range for analytics

        Returns:
            List of metric results
        """
        if not resources:
            return []

        zone_ids = [r.id for r in resources]
        analytics = self.client.fetch_dns_analytics(zone_ids, timeframe)
        results = []

        for resource in resources:
            data = analytics.get(resource.id, {})

            results.append(
                create_metric(
                    resource,
                    "query_count",
                    float(data.get("query_count", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource,
                    "noerror_count",
                    float(data.get("noerror_count", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource,
                    "nxdomain_count",
                    float(data.get("nxdomain_count", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource,
                    "servfail_count",
                    float(data.get("servfail_count", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )

        return results
