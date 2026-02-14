#!/usr/bin/env python3
"""Workers section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..constants import FREE_PLAN_DAILY_LIMIT
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class WorkersSection(CloudflareSection):
    """Section for Cloudflare Workers monitoring."""

    # Special resource ID for account-wide global stats
    USAGE_RESOURCE_ID = "_workers_usage"

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "workers"

    @property
    def resource_type(self) -> str:
        """Return the default per-item resource type.

        Returns:
            str: Resource type for worker script items.
        """
        return "worker"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for Workers checks.
        """
        return [
            MetricDefinition("requests", "sum", "Count"),
            MetricDefinition("errors", "sum", "Count"),
            # CPU Time quantiles
            MetricDefinition("cpu_time_p50", "p50", "Milliseconds"),
            MetricDefinition("cpu_time_p90", "p90", "Milliseconds"),
            MetricDefinition("cpu_time_p99", "p99", "Milliseconds"),
            MetricDefinition("cpu_time_p999", "p999", "Milliseconds"),
            # Wall Time quantiles (real time)
            MetricDefinition("wall_time_p50", "p50", "Milliseconds"),
            MetricDefinition("wall_time_p90", "p90", "Milliseconds"),
            MetricDefinition("wall_time_p99", "p99", "Milliseconds"),
            MetricDefinition("wall_time_p999", "p999", "Milliseconds"),
            # Duration quantiles (request duration)
            MetricDefinition("duration_p50", "p50", "Milliseconds"),
            MetricDefinition("duration_p90", "p90", "Milliseconds"),
            MetricDefinition("duration_p99", "p99", "Milliseconds"),
            MetricDefinition("duration_p999", "p999", "Milliseconds"),
            # Daily usage metrics (account-wide)
            MetricDefinition("daily_requests", "sum", "Count"),
            MetricDefinition("daily_limit", "gauge", "Count"),
            MetricDefinition("daily_usage_percent", "gauge", "Percent"),
            # Monthly usage metrics (account-wide)
            MetricDefinition("monthly_requests", "sum", "Count"),
            # Per-worker breakdown slots for stacked graph (account-wide)
            MetricDefinition("top1_requests", "sum", "Count"),
            MetricDefinition("top2_requests", "sum", "Count"),
            MetricDefinition("top3_requests", "sum", "Count"),
            MetricDefinition("top4_requests", "sum", "Count"),
            MetricDefinition("top5_requests", "sum", "Count"),
            MetricDefinition("other_requests", "sum", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all Workers scripts.

        Returns:
            List of Worker resources
        """
        workers = self.client.list_workers()

        # Add special resource for account-wide global stats (daily + monthly)
        resources = [
            Resource(
                id=self.USAGE_RESOURCE_ID,
                name="Workers Global",
                resource_type="workers_global",
                metadata={},
                available_metrics=[
                    "daily_requests",
                    "daily_limit",
                    "daily_usage_percent",
                    "monthly_requests",
                    "top1_requests",
                    "top2_requests",
                    "top3_requests",
                    "top4_requests",
                    "top5_requests",
                    "other_requests",
                ],
            )
        ]

        for worker in workers:
            worker_id = worker.get("id")
            if not worker_id:
                continue

            resources.append(
                Resource(
                    id=worker_id,
                    name=worker_id,  # Workers use ID as name
                    resource_type=self.resource_type,
                    metadata={
                        "created_on": worker.get("created_on"),
                        "modified_on": worker.get("modified_on"),
                        "etag": worker.get("etag"),
                    },
                    available_metrics=[
                        "requests",
                        "errors",
                        "daily_requests",
                        "cpu_time_p50",
                        "cpu_time_p90",
                        "cpu_time_p99",
                        "cpu_time_p999",
                        "wall_time_p50",
                        "wall_time_p90",
                        "wall_time_p99",
                        "wall_time_p999",
                        "duration_p50",
                        "duration_p90",
                        "duration_p99",
                        "duration_p999",
                    ],
                )
            )

        return resources

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch Workers analytics.

        Args:
            resources: List of Worker resources
            timeframe: Time range for analytics

        Returns:
            List of metric results
        """
        if not resources:
            return []

        # Separate global resource from worker resources
        global_resource = next((r for r in resources if r.id == self.USAGE_RESOURCE_ID), None)
        worker_resources = [r for r in resources if r.id != self.USAGE_RESOURCE_ID]
        worker_names = [r.id for r in worker_resources]

        results: list[MetricResult] = []

        # Fetch daily usage (always, regardless of timeframe)
        daily_usage = self.client.fetch_workers_daily_usage()
        requests_today = daily_usage.get("requests_today", 0)
        daily_limit = daily_usage.get("daily_limit", FREE_PLAN_DAILY_LIMIT)
        is_paid = daily_usage.get("is_paid_plan", False)
        per_worker = daily_usage.get("per_worker", {})

        # Calculate usage percentage
        usage_percent = (requests_today / daily_limit * 100) if daily_limit > 0 else 0.0

        # Add account-wide usage metrics (if global resource exists)
        if global_resource:
            paid_meta = {"is_paid_plan": is_paid}
            results.append(
                create_metric(
                    global_resource,
                    "daily_requests",
                    float(requests_today),
                    "Count",
                    "sum",
                    "today",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "daily_limit",
                    float(daily_limit),
                    "Count",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "daily_usage_percent",
                    float(usage_percent),
                    "Percent",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )

            # Fetch monthly usage
            monthly_usage = self.client.fetch_workers_monthly_usage()
            monthly_requests = monthly_usage.get("requests_month", 0)
            results.append(
                create_metric(
                    global_resource,
                    "monthly_requests",
                    float(monthly_requests),
                    "Count",
                    "sum",
                    "month",
                    paid_meta,
                )
            )

            # Per-worker breakdown for stacked graph (Top 5 + Other)
            sorted_workers = sorted(per_worker.items(), key=lambda x: (-x[1], x[0]))

            # Top 5 workers get individual slots
            for i in range(5):
                if i < len(sorted_workers):
                    worker_name, count = sorted_workers[i]
                    results.append(
                        create_metric(
                            global_resource,
                            f"top{i + 1}_requests",
                            float(count),
                            "Count",
                            "sum",
                            "today",
                            {"worker_name": worker_name},
                        )
                    )
                else:
                    results.append(
                        create_metric(
                            global_resource, f"top{i + 1}_requests", 0.0, "Count", "sum", "today"
                        )
                    )

            # Aggregate remaining workers as "other"
            other_workers = sorted_workers[5:]
            other_count = sum(count for _, count in other_workers)
            other_names = [name for name, _ in other_workers]
            results.append(
                create_metric(
                    global_resource,
                    "other_requests",
                    float(other_count),
                    "Count",
                    "sum",
                    "today",
                    {"worker_names": other_names, "count": len(other_names)},
                )
            )

        # Fetch per-worker analytics for the configured timeframe
        if worker_names:
            analytics = self.client.fetch_workers_analytics(worker_names, timeframe)

            for resource in worker_resources:
                data = analytics.get(resource.id, {})
                worker_daily = per_worker.get(resource.id, 0)

                # Basic metrics
                results.append(
                    create_metric(
                        resource,
                        "requests",
                        float(data.get("requests", 0)),
                        "Count",
                        "sum",
                        timeframe,
                    )
                )
                results.append(
                    create_metric(
                        resource, "errors", float(data.get("errors", 0)), "Count", "sum", timeframe
                    )
                )

                # CPU Time quantiles
                for percentile in ["p50", "p90", "p99", "p999"]:
                    results.append(
                        create_metric(
                            resource,
                            f"cpu_time_{percentile}",
                            float(data.get(f"cpu_time_{percentile}", 0)),
                            "Milliseconds",
                            percentile,
                            timeframe,
                        )
                    )

                # Wall Time quantiles
                for percentile in ["p50", "p90", "p99", "p999"]:
                    results.append(
                        create_metric(
                            resource,
                            f"wall_time_{percentile}",
                            float(data.get(f"wall_time_{percentile}", 0)),
                            "Milliseconds",
                            percentile,
                            timeframe,
                        )
                    )

                # Duration quantiles
                for percentile in ["p50", "p90", "p99", "p999"]:
                    results.append(
                        create_metric(
                            resource,
                            f"duration_{percentile}",
                            float(data.get(f"duration_{percentile}", 0)),
                            "Milliseconds",
                            percentile,
                            timeframe,
                        )
                    )

                # Daily requests per worker
                results.append(
                    create_metric(
                        resource, "daily_requests", float(worker_daily), "Count", "sum", "today"
                    )
                )

        return results
