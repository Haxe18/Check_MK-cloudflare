#!/usr/bin/env python3
"""Zone Analytics section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class ZoneAnalyticsSection(CloudflareSection):
    """Section for Cloudflare Zone Analytics monitoring.

    Monitors HTTP traffic analytics per zone including:
    - Total requests
    - Bandwidth (bytes)
    - Threats blocked
    - Page views
    - Cached requests and bandwidth
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "zone_analytics"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for zone analytics items.
        """
        return "zone"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for zone analytics checks.
        """
        return [
            MetricDefinition("requests", "sum", "Count"),
            MetricDefinition("bandwidth", "sum", "Bytes"),
            MetricDefinition("threats", "sum", "Count"),
            MetricDefinition("page_views", "sum", "Count"),
            MetricDefinition("cached_requests", "sum", "Count"),
            MetricDefinition("cached_bandwidth", "sum", "Bytes"),
            MetricDefinition("cache_hit_ratio", "avg", "Percent"),
            # Time to First Byte (TTFB) - Pro+ plans
            MetricDefinition("ttfb_p50", "p50", "Milliseconds"),
            MetricDefinition("ttfb_p95", "p95", "Milliseconds"),
            MetricDefinition("ttfb_p99", "p99", "Milliseconds"),
            # Origin Response Duration - Pro+ plans
            MetricDefinition("origin_response_p50", "p50", "Milliseconds"),
            MetricDefinition("origin_response_p95", "p95", "Milliseconds"),
            MetricDefinition("origin_response_p99", "p99", "Milliseconds"),
            # Edge DNS Response Time - Pro+ plans
            MetricDefinition("edge_dns_p50", "p50", "Milliseconds"),
            MetricDefinition("edge_dns_p95", "p95", "Milliseconds"),
            MetricDefinition("edge_dns_p99", "p99", "Milliseconds"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all DNS zones for analytics."""
        return self._discover_zones(include_plan=True)

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch zone HTTP analytics.

        Args:
            resources: List of zone resources
            timeframe: Time range for analytics

        Returns:
            List of metric results
        """
        if not resources:
            return []

        zone_ids = [r.id for r in resources]

        # Build zone_id -> plan mapping to skip Pro+ metrics for Free zones
        zone_plans = {r.id: r.metadata.get("plan", "Free") for r in resources}

        analytics = self.client.fetch_zone_analytics(zone_ids, zone_plans, timeframe)
        results: list[MetricResult] = []

        for resource in resources:
            data = analytics.get(resource.id, {})

            requests = float(data.get("requests", 0))
            cached_requests = float(data.get("cached_requests", 0))

            # Calculate cache hit ratio
            cache_hit_ratio = (cached_requests / requests * 100) if requests > 0 else 0.0

            # Basic metrics
            results.append(create_metric(resource, "requests", requests, "Count", "sum", timeframe))
            results.append(
                create_metric(
                    resource,
                    "bandwidth",
                    float(data.get("bandwidth", 0)),
                    "Bytes",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource, "threats", float(data.get("threats", 0)), "Count", "sum", timeframe
                )
            )
            results.append(
                create_metric(
                    resource,
                    "page_views",
                    float(data.get("page_views", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource, "cached_requests", cached_requests, "Count", "sum", timeframe
                )
            )
            results.append(
                create_metric(
                    resource,
                    "cached_bandwidth",
                    float(data.get("cached_bandwidth", 0)),
                    "Bytes",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource, "cache_hit_ratio", cache_hit_ratio, "Percent", "avg", timeframe
                )
            )

            # Performance metrics (Pro+ plans) - TTFB
            for percentile in ["p50", "p95", "p99"]:
                results.append(
                    create_metric(
                        resource,
                        f"ttfb_{percentile}",
                        float(data.get(f"ttfb_{percentile}", 0)),
                        "Milliseconds",
                        percentile,
                        timeframe,
                    )
                )

            # Origin Response Duration (Pro+ plans)
            for percentile in ["p50", "p95", "p99"]:
                results.append(
                    create_metric(
                        resource,
                        f"origin_response_{percentile}",
                        float(data.get(f"origin_response_{percentile}", 0)),
                        "Milliseconds",
                        percentile,
                        timeframe,
                    )
                )

            # Edge DNS Response Time (Pro+ plans)
            for percentile in ["p50", "p95", "p99"]:
                results.append(
                    create_metric(
                        resource,
                        f"edge_dns_{percentile}",
                        float(data.get(f"edge_dns_{percentile}", 0)),
                        "Milliseconds",
                        percentile,
                        timeframe,
                    )
                )

        return results
