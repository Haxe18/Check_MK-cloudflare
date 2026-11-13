#!/usr/bin/env python3
"""Pages section for Cloudflare monitoring."""

from datetime import datetime, timezone

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class PagesSection(CloudflareSection):
    """Section for Cloudflare Pages monitoring."""

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "pages"

    @property
    def resource_type(self) -> str:
        """Return the resource type identifier.

        Returns:
            str: Resource type for Pages project items.
        """
        return "pages_project"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for Pages checks.
        """
        return [
            # Deployment-Status metrics
            MetricDefinition("deployment_status", "gauge", "Status"),
            MetricDefinition("deployment_age_seconds", "gauge", "Seconds"),
            MetricDefinition("domains_count", "gauge", "Count"),
            # Pages Functions metrics (only for projects with Functions)
            MetricDefinition("invocations", "sum", "Count"),
            MetricDefinition("errors", "sum", "Count"),
            MetricDefinition("cpu_time_p50", "p50", "Milliseconds"),
            MetricDefinition("cpu_time_p99", "p99", "Milliseconds"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all Pages projects.

        Returns:
            List of Pages project resources
        """
        projects = self.client.list_pages_projects()
        resources = []

        for project in projects:
            project_name = project.get("name")
            if not project_name:
                continue

            # Extract project metadata
            uses_functions = project.get("uses_functions", False)
            subdomain = project.get("subdomain", "")
            domains = project.get("domains", [])
            production_branch = project.get("production_branch", "main")
            created_on = project.get("created_on", "")

            # Get canonical deployment info
            canonical = project.get("canonical_deployment") or {}
            canonical_url = canonical.get("url", "")

            # Determine available metrics based on whether Functions are used
            available_metrics = [
                "deployment_status",
                "deployment_age_seconds",
                "domains_count",
            ]

            if uses_functions:
                available_metrics.extend(
                    [
                        "invocations",
                        "errors",
                        "cpu_time_p50",
                        "cpu_time_p99",
                    ]
                )

            resources.append(
                Resource(
                    id=project_name,  # Use name as ID (unique per account)
                    name=project_name,
                    resource_type=self.resource_type,
                    metadata={
                        "uses_functions": uses_functions,
                        "subdomain": subdomain,
                        "domains": domains,
                        "domains_count": len(domains),
                        "production_branch": production_branch,
                        "created_on": created_on,
                        "canonical_url": canonical_url,
                    },
                    available_metrics=available_metrics,
                )
            )

        return resources

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch Pages analytics.

        Args:
            resources: List of Pages project resources
            timeframe: Time range for analytics

        Returns:
            List of metric results
        """
        if not resources:
            return []

        results: list[MetricResult] = []

        # Separate projects with and without Functions
        function_projects = [r for r in resources if r.metadata.get("uses_functions", False)]
        function_project_names = [r.id for r in function_projects]

        # Fetch Functions analytics for projects that use them
        functions_analytics = {}
        if function_project_names:
            functions_analytics = self.client.fetch_pages_functions_analytics(
                function_project_names, timeframe
            )

        # Process each project
        for resource in resources:
            project_name = resource.id

            # Fetch latest production deployment
            deployments = self.client.get_pages_deployments(
                project_name, limit=1, environment="production"
            )

            # Find the latest production deployment
            production_deployment = None
            for deployment in deployments:
                if deployment.get("environment") == "production":
                    production_deployment = deployment
                    break

            # Calculate deployment status and age
            if production_deployment:
                deployment_status, status_text = self._get_deployment_status(production_deployment)
                deployment_age = self._get_deployment_age(production_deployment)
                deployment_url = production_deployment.get("url", "")
                deployment_id = production_deployment.get("short_id", "")
            else:
                deployment_status = 2  # No deployment = error state
                status_text = "no_deployment"
                deployment_age = 0
                deployment_url = ""
                deployment_id = ""

            # Add deployment status metrics
            results.append(
                create_metric(
                    resource,
                    "deployment_status",
                    float(deployment_status),
                    "Status",
                    "gauge",
                    timeframe,
                    {
                        "status_text": status_text,
                        "deployment_url": deployment_url,
                        "deployment_id": deployment_id,
                    },
                )
            )

            results.append(
                create_metric(
                    resource,
                    "deployment_age_seconds",
                    float(deployment_age),
                    "Seconds",
                    "gauge",
                    timeframe,
                )
            )

            results.append(
                create_metric(
                    resource,
                    "domains_count",
                    float(resource.metadata.get("domains_count", 0)),
                    "Count",
                    "gauge",
                    timeframe,
                    {"domains": resource.metadata.get("domains", [])},
                )
            )

            # Add Functions analytics if available
            if resource.metadata.get("uses_functions", False):
                func_data = functions_analytics.get(project_name, {})

                results.append(
                    create_metric(
                        resource,
                        "invocations",
                        float(func_data.get("requests", 0)),
                        "Count",
                        "sum",
                        timeframe,
                    )
                )

                results.append(
                    create_metric(
                        resource,
                        "errors",
                        float(func_data.get("errors", 0)),
                        "Count",
                        "sum",
                        timeframe,
                    )
                )

                # CPU Time quantiles
                results.append(
                    create_metric(
                        resource,
                        "cpu_time_p50",
                        float(func_data.get("cpu_time_p50", 0)),
                        "Milliseconds",
                        "p50",
                        timeframe,
                    )
                )

                results.append(
                    create_metric(
                        resource,
                        "cpu_time_p99",
                        float(func_data.get("cpu_time_p99", 0)),
                        "Milliseconds",
                        "p99",
                        timeframe,
                    )
                )

        return results

    @staticmethod
    def _get_deployment_status(deployment: dict) -> tuple[int, str]:
        """Get deployment status code and text.

        Args:
            deployment: Deployment object

        Returns:
            Tuple of (status_code, status_text)
            0 = OK (success)
            1 = Building (active)
            2 = Failed (failure/error)
        """
        latest_stage = deployment.get("latest_stage", {})
        status = latest_stage.get("status", "unknown")

        if status == "success":
            return 0, "success"
        if status == "active":
            return 1, "building"
        if status in ("failure", "canceled"):
            return 2, status
        if status == "idle":
            # Idle usually means queued, treat as building
            return 1, "queued"
        return 2, f"unknown:{status}"

    @staticmethod
    def _get_deployment_age(deployment: dict) -> int:
        """Get age of deployment in seconds.

        Args:
            deployment: Deployment object

        Returns:
            Age in seconds since created_on
        """
        created_on = deployment.get("created_on", "")
        if not created_on:
            return 0

        try:
            # Parse ISO timestamp
            created_dt = datetime.fromisoformat(created_on.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = (now - created_dt).total_seconds()
            return max(0, int(age))
        except (ValueError, TypeError):
            return 0
