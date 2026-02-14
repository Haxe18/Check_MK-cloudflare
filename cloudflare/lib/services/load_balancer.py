#!/usr/bin/env python3
"""Load Balancer section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class LoadBalancerSection(CloudflareSection):
    """Section for Cloudflare Load Balancer monitoring.

    Monitors load balancers and pools including:
    - Pool count
    - Healthy origins
    - Pool health status
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "load_balancer"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for load balancer pool items.
        """
        return "load_balancer_pool"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for load balancer checks.
        """
        return [
            MetricDefinition("healthy", "gauge", "Boolean"),
            MetricDefinition("origin_count", "gauge", "Count"),
            MetricDefinition("healthy_origin_count", "gauge", "Count"),
            # Health check RTT
            MetricDefinition("health_rtt_avg", "avg", "Milliseconds"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all Load Balancer pools.

        Returns:
            List of pool resources
        """
        pools = self.client.list_load_balancer_pools()
        resources = []

        for pool in pools:
            pool_id = pool.get("id")
            if not pool_id:
                continue

            origins = pool.get("origins", [])

            resources.append(
                Resource(
                    id=pool_id,
                    name=pool.get("name", pool_id),
                    resource_type=self.resource_type,
                    metadata={
                        "name": pool.get("name"),
                        "enabled": pool.get("enabled", True),
                        "minimum_origins": pool.get("minimum_origins", 1),
                        "monitor": pool.get("monitor"),
                        "origins": origins,
                        "origin_count": len(origins),
                        "created_on": pool.get("created_on"),
                        "modified_on": pool.get("modified_on"),
                    },
                    available_metrics=[m.name for m in self.metrics],
                )
            )

        return resources

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch Load Balancer pool metrics.

        Args:
            resources: List of pool resources
            timeframe: Time range (not used for status)

        Returns:
            List of metric results
        """
        results = []

        for resource in resources:
            # Fetch pool health
            health = self.client.get_pool_health(resource.id)

            # Pool health status
            pool_healthy = health.get("healthy", False) if health else False

            # Count origins
            origins = resource.metadata.get("origins", [])
            origin_count = len(origins)

            # Count healthy origins from health data and collect RTT
            healthy_origin_count = 0
            rtt_values: list[float] = []
            if health:
                origins_health = health.get("origins", {})
                for origin_health in origins_health.values():
                    if origin_health.get("healthy", False):
                        healthy_origin_count += 1
                    # Collect RTT from healthy origins
                    rtt = origin_health.get("rtt")
                    if rtt is not None and rtt > 0:
                        rtt_values.append(float(rtt))

            # Calculate average RTT (in milliseconds)
            avg_rtt = (sum(rtt_values) / len(rtt_values)) if rtt_values else 0.0

            # Healthy status
            results.append(
                create_metric(
                    resource,
                    "healthy",
                    1.0 if pool_healthy else 0.0,
                    "Boolean",
                    "gauge",
                    timeframe,
                    extra_metadata={"healthy": pool_healthy},
                )
            )

            # Origin Count
            results.append(
                create_metric(
                    resource, "origin_count", float(origin_count), "Count", "gauge", timeframe
                )
            )

            # Healthy Origin Count
            results.append(
                create_metric(
                    resource,
                    "healthy_origin_count",
                    float(healthy_origin_count),
                    "Count",
                    "gauge",
                    timeframe,
                )
            )

            # Health Check RTT
            results.append(
                create_metric(resource, "health_rtt_avg", avg_rtt, "Milliseconds", "avg", timeframe)
            )

        return results
