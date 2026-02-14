#!/usr/bin/env python3
"""KV Namespaces section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class KVSection(CloudflareSection):
    """Section for Cloudflare KV Namespaces monitoring."""

    # Special resource ID for account-wide global stats
    USAGE_RESOURCE_ID = "_kv_usage"

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "kv"

    @property
    def resource_type(self) -> str:
        """Return the default per-item resource type.

        Returns:
            str: Resource type for KV namespace items.
        """
        return "kv_namespace"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for KV checks.
        """
        return [
            MetricDefinition("reads", "sum", "Count"),
            MetricDefinition("writes", "sum", "Count"),
            MetricDefinition("deletes", "sum", "Count"),
            MetricDefinition("lists", "sum", "Count"),
            MetricDefinition("key_count", "gauge", "Count"),
            MetricDefinition("storage_bytes", "gauge", "Bytes"),
            # Latency quantiles (matching Cloudflare dashboard: P50, P75, P90, P99)
            MetricDefinition("latency_p50", "p50", "Milliseconds"),
            MetricDefinition("latency_p75", "p75", "Milliseconds"),
            MetricDefinition("latency_p90", "p90", "Milliseconds"),
            MetricDefinition("latency_p99", "p99", "Milliseconds"),
            # Read status (hot/cold/not_found)
            MetricDefinition("hot_reads", "sum", "Count"),
            MetricDefinition("cold_reads", "sum", "Count"),
            MetricDefinition("not_found", "sum", "Count"),
            # Monthly summary
            MetricDefinition("reads_month", "sum", "Count"),
            MetricDefinition("writes_month", "sum", "Count"),
            MetricDefinition("lists_month", "sum", "Count"),
            MetricDefinition("deletes_month", "sum", "Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all KV namespaces.

        Returns:
            List of KV namespace resources
        """
        namespaces = self.client.list_kv_namespaces()

        # Add special resource for account-wide global stats
        resources = [
            Resource(
                id=self.USAGE_RESOURCE_ID,
                name="KV Global",
                resource_type="kv_global",
                metadata={"_namespace_ids": [ns.get("id") for ns in namespaces if ns.get("id")]},
                available_metrics=[
                    "daily_reads",
                    "reads_limit",
                    "daily_writes",
                    "writes_limit",
                    "daily_deletes",
                    "deletes_limit",
                    "daily_lists",
                    "lists_limit",
                ],
            )
        ]

        for namespace in namespaces:
            namespace_id = namespace.get("id")
            if not namespace_id:
                continue

            resources.append(
                Resource(
                    id=namespace_id,
                    name=namespace.get("title", namespace_id),
                    resource_type=self.resource_type,
                    metadata={
                        "title": namespace.get("title"),
                        "supports_url_encoding": namespace.get("supports_url_encoding"),
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
        """Fetch KV namespace analytics.

        Args:
            resources: List of KV namespace resources
            timeframe: Time range for analytics

        Returns:
            List of metric results
        """
        if not resources:
            return []

        # Separate global resource from namespace resources
        global_resource = next((r for r in resources if r.id == self.USAGE_RESOURCE_ID), None)
        ns_resources = [r for r in resources if r.id != self.USAGE_RESOURCE_ID]
        namespace_ids = [r.id for r in ns_resources]

        results: list[MetricResult] = []

        # Fetch account-wide usage (always, regardless of timeframe)
        if global_resource:
            ns_ids = global_resource.metadata.get("_namespace_ids", namespace_ids)
            usage = self.client.fetch_kv_account_usage(ns_ids)
            is_paid = usage.get("is_paid_plan", False)
            paid_meta = {"is_paid_plan": is_paid}

            for key in [
                "daily_reads",
                "reads_limit",
                "daily_writes",
                "writes_limit",
                "daily_deletes",
                "deletes_limit",
                "daily_lists",
                "lists_limit",
            ]:
                results.append(
                    create_metric(
                        global_resource,
                        key,
                        float(usage.get(key, 0)),
                        "Count",
                        "gauge",
                        "today",
                        paid_meta,
                    )
                )

            results.append(
                create_metric(
                    global_resource,
                    "total_namespaces",
                    float(usage.get("total_namespaces", 0)),
                    "Count",
                    "gauge",
                    "now",
                    paid_meta,
                )
            )

        # Fetch per-namespace analytics
        if not ns_resources:
            return results

        analytics = self.client.fetch_kv_analytics(namespace_ids, timeframe)
        read_status = self.client.fetch_kv_read_status(namespace_ids, timeframe)
        monthly_summary = self.client.fetch_kv_monthly_summary(namespace_ids)

        for resource in ns_resources:
            data = analytics.get(resource.id, {})

            # Operations metrics
            results.append(
                create_metric(
                    resource, "reads", float(data.get("reads", 0)), "Count", "sum", timeframe
                )
            )
            results.append(
                create_metric(
                    resource, "writes", float(data.get("writes", 0)), "Count", "sum", timeframe
                )
            )
            results.append(
                create_metric(
                    resource, "deletes", float(data.get("deletes", 0)), "Count", "sum", timeframe
                )
            )
            results.append(
                create_metric(
                    resource, "lists", float(data.get("lists", 0)), "Count", "sum", timeframe
                )
            )

            # Storage metrics
            results.append(
                create_metric(
                    resource,
                    "key_count",
                    float(data.get("key_count", 0)),
                    "Count",
                    "gauge",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource,
                    "storage_bytes",
                    float(data.get("storage_bytes", 0)),
                    "Bytes",
                    "gauge",
                    timeframe,
                )
            )

            # Latency quantiles
            for percentile in ["p50", "p75", "p90", "p99"]:
                results.append(
                    create_metric(
                        resource,
                        f"latency_{percentile}",
                        float(data.get(f"latency_{percentile}", 0)),
                        "Milliseconds",
                        percentile,
                        timeframe,
                    )
                )

            # Read status (hot/cold/not_found)
            read_data = read_status.get(resource.id, {})
            results.append(
                create_metric(
                    resource,
                    "hot_reads",
                    float(read_data.get("hot_read", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource,
                    "cold_reads",
                    float(read_data.get("cold_read", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )
            results.append(
                create_metric(
                    resource,
                    "not_found",
                    float(read_data.get("not_found", 0)),
                    "Count",
                    "sum",
                    timeframe,
                )
            )

            # Monthly summary
            monthly = monthly_summary.get(resource.id, {})
            results.append(
                create_metric(
                    resource, "reads_month", float(monthly.get("reads", 0)), "Count", "sum", "month"
                )
            )
            results.append(
                create_metric(
                    resource,
                    "writes_month",
                    float(monthly.get("writes", 0)),
                    "Count",
                    "sum",
                    "month",
                )
            )
            results.append(
                create_metric(
                    resource, "lists_month", float(monthly.get("lists", 0)), "Count", "sum", "month"
                )
            )
            results.append(
                create_metric(
                    resource,
                    "deletes_month",
                    float(monthly.get("deletes", 0)),
                    "Count",
                    "sum",
                    "month",
                )
            )

        return results
