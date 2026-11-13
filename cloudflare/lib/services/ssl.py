#!/usr/bin/env python3
"""SSL/TLS section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource


class SSLSection(CloudflareSection):
    """Section for Cloudflare SSL/TLS monitoring.

    Monitors the SSL/TLS encryption mode per zone (off/flexible/full/strict).
    Certificates themselves are not checked: 'certificate_status' only says whether
    SSL is switched on (active), switched off (disabled) or could not be read (unknown).
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
            # Get SSL mode setting
            ssl_setting = self.client.get_ssl_setting(resource.id)
            ssl_mode = ssl_setting.get("value") if ssl_setting else None

            if ssl_mode is None:
                # API call failed - the SSL mode is not known
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
