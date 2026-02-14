#!/usr/bin/env python3
"""Access section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class AccessSection(CloudflareSection):
    """Section for Cloudflare Access monitoring.

    Monitors Access applications and policies including:
    - Application count
    - Policy count per app
    - Application status
    """

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "access"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for discovered items.
        """
        return "access_app"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for Access checks.
        """
        return [
            MetricDefinition("policy_count", "gauge", "Count"),
            MetricDefinition("allowed_idps_count", "gauge", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all Access applications.

        Returns:
            List of Access application resources
        """
        apps = self.client.list_access_apps()
        resources = []

        for app in apps:
            app_id = app.get("id")
            if not app_id:
                continue

            resources.append(
                Resource(
                    id=app_id,
                    name=app.get("name", app_id),
                    resource_type=self.resource_type,
                    metadata={
                        "name": app.get("name"),
                        "domain": app.get("domain"),
                        "type": app.get("type"),
                        "session_duration": app.get("session_duration"),
                        "allowed_idps": app.get("allowed_idps", []),
                        "created_at": app.get("created_at"),
                        "updated_at": app.get("updated_at"),
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
        """Fetch Access application metrics.

        Args:
            resources: List of Access application resources
            timeframe: Time range (not used for status)

        Returns:
            List of metric results
        """
        results = []

        for resource in resources:
            # Fetch policies for this app
            policies = self.client.list_access_policies(resource.id)
            policy_count = len(policies)

            # Count allowed IDPs
            allowed_idps = resource.metadata.get("allowed_idps", [])
            allowed_idps_count = len(allowed_idps)

            # Policy Count
            results.append(
                create_metric(
                    resource,
                    "policy_count",
                    float(policy_count),
                    "Count",
                    "gauge",
                    timeframe,
                    extra_metadata={"domain": resource.metadata.get("domain")},
                )
            )

            # Allowed IDPs Count
            results.append(
                create_metric(
                    resource,
                    "allowed_idps_count",
                    float(allowed_idps_count),
                    "Count",
                    "gauge",
                    timeframe,
                    extra_metadata={"domain": resource.metadata.get("domain")},
                )
            )

        return results
