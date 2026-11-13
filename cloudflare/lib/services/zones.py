#!/usr/bin/env python3
"""DNS Zones section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class ZonesSection(CloudflareSection):
    """Section for Cloudflare DNS Zones monitoring."""

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "zones"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for zone items.
        """
        return "zone"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for zone status checks.
        """
        return [
            MetricDefinition("status", "gauge", "Status"),
            MetricDefinition("paused", "gauge", "Boolean"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all DNS zones.

        Returns:
            List of zone resources
        """
        zones = self.client.list_zones()
        resources = []

        for zone in zones:
            zone_id = zone.get("id")
            if not zone_id:
                continue

            resources.append(
                Resource(
                    id=zone_id,
                    name=zone.get("name", zone_id),
                    resource_type=self.resource_type,
                    metadata={
                        "name": zone.get("name"),
                        "status": zone.get("status"),
                        "paused": zone.get("paused", False),
                        "type": zone.get("type"),
                        "name_servers": zone.get("name_servers", []),
                        "original_name_servers": zone.get("original_name_servers", []),
                        "created_on": zone.get("created_on"),
                        "modified_on": zone.get("modified_on"),
                        "plan": zone.get("plan", {}).get("name"),
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
        """Fetch zone status metrics.

        Args:
            resources: List of zone resources
            timeframe: Time range (not used for status)

        Returns:
            List of metric results
        """
        results = []

        # Status and paused in the resource metadata are as old as the discovery cache,
        # so read the current ones; the cached values are the fallback if that fails
        current_zones = {zone.get("id"): zone for zone in self.client.list_zones()}

        for resource in resources:
            current_zone = current_zones.get(resource.id, resource.metadata)
            status = current_zone.get("status") or "unknown"
            paused = current_zone.get("paused", False)

            # Status as numeric value (1 = active, 0 = other)
            status_value = 1.0 if status == "active" else 0.0

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

            results.append(
                create_metric(
                    resource,
                    "paused",
                    1.0 if paused else 0.0,
                    "Boolean",
                    "gauge",
                    timeframe,
                    extra_metadata={"paused": paused},
                )
            )

        return results
