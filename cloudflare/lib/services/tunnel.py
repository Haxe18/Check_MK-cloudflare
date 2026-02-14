#!/usr/bin/env python3
"""Tunnel section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class TunnelSection(CloudflareSection):
    """Section for Cloudflare Tunnel monitoring.

    Monitors tunnels including:
    - Tunnel status
    - Connection count
    - Connection details
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "tunnel"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for tunnel items.
        """
        return "tunnel"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for tunnel checks.
        """
        return [
            MetricDefinition("status", "gauge", "Status"),
            MetricDefinition("connection_count", "gauge", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all Cloudflare Tunnels.

        Returns:
            List of Tunnel resources
        """
        tunnels = self.client.list_tunnels()
        resources = []

        for tunnel in tunnels:
            tunnel_id = tunnel.get("id")
            if not tunnel_id:
                continue

            status = tunnel.get("status", "unknown")

            resources.append(
                Resource(
                    id=tunnel_id,
                    name=tunnel.get("name", tunnel_id),
                    resource_type=self.resource_type,
                    metadata={
                        "name": tunnel.get("name"),
                        "status": status,
                        "created_at": tunnel.get("created_at"),
                        "deleted_at": tunnel.get("deleted_at"),
                        "conns_active_at": tunnel.get("conns_active_at"),
                        "remote_config": tunnel.get("remote_config", False),
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
        """Fetch Tunnel metrics.

        Args:
            resources: List of Tunnel resources
            timeframe: Time range (not used for status)

        Returns:
            List of metric results
        """
        results = []

        for resource in resources:
            status = resource.metadata.get("status", "unknown")

            # Status as numeric value
            # active = 2, inactive = 1, unknown = 0
            if status == "active":
                status_value = 2.0
            elif status == "inactive":
                status_value = 1.0
            else:
                status_value = 0.0

            # Fetch connections
            connections = self.client.get_tunnel_connections(resource.id)
            connection_count = len(connections)

            # Status
            results.append(
                create_metric(
                    resource,
                    "status",
                    status_value,
                    "Status",
                    "gauge",
                    timeframe,
                    extra_metadata={"status_text": status},
                )
            )

            # Connection Count
            results.append(
                create_metric(
                    resource,
                    "connection_count",
                    float(connection_count),
                    "Count",
                    "gauge",
                    timeframe,
                    extra_metadata={"status_text": status},
                )
            )

        return results
