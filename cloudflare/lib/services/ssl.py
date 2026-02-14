#!/usr/bin/env python3
"""SSL/TLS section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource


class SSLSection(CloudflareSection):
    """Section for Cloudflare SSL/TLS monitoring.

    Monitors SSL/TLS status per zone including:
    - Certificate status (active/pending/inactive)
    - SSL mode (off/flexible/full/strict)
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "ssl"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for zone SSL items.
        """
        return "zone"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Empty list (status-only check).
        """
        return []  # Keine Metriken - reiner Status-Check

    def discover_resources(self) -> list[Resource]:
        """Discover all zones for SSL monitoring.

        Returns:
            List of zone resources
        """
        return self._discover_zones()

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,  # pylint: disable=unused-argument
    ) -> list[MetricResult]:
        """Fetch SSL/TLS status for zones.

        Stores SSL data in resource metadata (no metrics/graphs needed).

        Args:
            resources: List of zone resources
            timeframe: Time range (not used for status)

        Returns:
            Empty list - SSL is a pure status check without metrics
        """
        for resource in resources:
            # Get zone status from metadata (set during discovery)
            zone_status = resource.metadata.get("status", "unknown")

            # Get SSL mode setting
            ssl_setting = self.client.get_ssl_setting(resource.id)
            ssl_mode = ssl_setting.get("value") if ssl_setting else None

            if ssl_mode is None:
                # API call failed - if zone is active, assume SSL is working
                if zone_status == "active":
                    resource.metadata["certificate_status"] = "active"
                    resource.metadata["ssl_mode"] = "unknown"
                else:
                    resource.metadata["certificate_status"] = "unknown"
                    resource.metadata["ssl_mode"] = "unknown"
            elif ssl_mode == "off":
                resource.metadata["certificate_status"] = "disabled"
                resource.metadata["ssl_mode"] = "off"
            else:
                # SSL is enabled (flexible/full/strict)
                resource.metadata["certificate_status"] = "active"
                resource.metadata["ssl_mode"] = ssl_mode

        return []  # Keine Metriken
