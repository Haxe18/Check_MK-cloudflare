#!/usr/bin/env python3
"""D1 Database section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class D1Section(CloudflareSection):
    """Section for Cloudflare D1 Database monitoring.

    Monitors D1 databases including:
    - Database presence and version
    - Creation date
    - Account-wide usage vs plan limits
    """

    # Special resource ID for account-wide global stats
    USAGE_RESOURCE_ID = "_d1_usage"

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "d1"

    @property
    def resource_type(self) -> str:
        """Return the default per-item resource type.

        Returns:
            str: Resource type for D1 database items.
        """
        return "d1_database"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for D1 checks.
        """
        return [
            MetricDefinition("status", "gauge", "Status"),
            MetricDefinition("storage_bytes", "gauge", "Storage Size"),
            MetricDefinition("query_count", "counter", "Query Count"),
            MetricDefinition("read_rows", "counter", "Rows Read"),
            MetricDefinition("write_rows", "counter", "Rows Written"),
            MetricDefinition("duration_avg", "gauge", "Avg Duration"),
            # Account-wide usage metrics
            MetricDefinition("total_databases", "gauge", "Count"),
            MetricDefinition("max_databases", "gauge", "Count"),
            MetricDefinition("total_storage", "gauge", "Bytes"),
            MetricDefinition("max_storage", "gauge", "Bytes"),
            MetricDefinition("daily_rows_read", "gauge", "Count"),
            MetricDefinition("daily_rows_read_limit", "gauge", "Count"),
            MetricDefinition("daily_rows_written", "gauge", "Count"),
            MetricDefinition("daily_rows_written_limit", "gauge", "Count"),
            MetricDefinition("storage_usage_percent", "gauge", "Percent"),
            MetricDefinition("rows_read_usage_percent", "gauge", "Percent"),
            MetricDefinition("rows_written_usage_percent", "gauge", "Percent"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all D1 databases.

        Returns:
            List of D1 database resources
        """
        databases = self.client.list_d1_databases()

        # Add special resource for account-wide global stats
        resources = [
            Resource(
                id=self.USAGE_RESOURCE_ID,
                name="D1 Global",
                resource_type="d1_global",
                metadata={"_databases": databases},
                available_metrics=[
                    "total_databases",
                    "max_databases",
                    "total_storage",
                    "max_storage",
                    "daily_rows_read",
                    "daily_rows_read_limit",
                    "daily_rows_written",
                    "daily_rows_written_limit",
                    "storage_usage_percent",
                    "rows_read_usage_percent",
                    "rows_written_usage_percent",
                ],
            )
        ]

        for database in databases:
            db_id = database.get("uuid")
            db_name = database.get("name")
            if not db_id or not db_name:
                continue

            resources.append(
                Resource(
                    id=db_id,
                    name=db_name,
                    resource_type=self.resource_type,
                    metadata={
                        "name": db_name,
                        "version": database.get("version", "unknown"),
                        "created_at": database.get("created_at"),
                    },
                    available_metrics=[m.name for m in self.metrics[:6]],
                )
            )

        return resources

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch D1 database metrics.

        Args:
            resources: List of D1 database resources
            timeframe: Time range (not used for status)

        Returns:
            List of metric results
        """
        results = []

        # Separate global resource from database resources
        global_resource = next((r for r in resources if r.id == self.USAGE_RESOURCE_ID), None)
        db_resources = [r for r in resources if r.id != self.USAGE_RESOURCE_ID]
        db_ids = [r.id for r in db_resources]

        # Sizes are not part of the database list, so they are read per database
        file_sizes = self.client.fetch_d1_file_sizes(db_ids)

        # Fetch account-wide usage (always, regardless of timeframe)
        if global_resource:
            databases = global_resource.metadata.get("_databases", [])
            usage = self.client.fetch_d1_daily_usage(len(databases), sum(file_sizes.values()))
            is_paid = usage.get("is_paid_plan", False)
            paid_meta = {"is_paid_plan": is_paid}

            results.append(
                create_metric(
                    global_resource,
                    "total_databases",
                    float(usage["total_databases"]),
                    "Count",
                    "gauge",
                    "now",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "max_databases",
                    float(usage["max_databases"]),
                    "Count",
                    "gauge",
                    "now",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "total_storage",
                    float(usage["total_storage"]),
                    "Bytes",
                    "gauge",
                    "now",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "max_storage",
                    float(usage["max_storage"]),
                    "Bytes",
                    "gauge",
                    "now",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "daily_rows_read",
                    float(usage["daily_rows_read"]),
                    "Count",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "daily_rows_read_limit",
                    float(usage["daily_rows_read_limit"]),
                    "Count",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "daily_rows_written",
                    float(usage["daily_rows_written"]),
                    "Count",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "daily_rows_written_limit",
                    float(usage["daily_rows_written_limit"]),
                    "Count",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )

            # Calculate usage percentages
            max_storage = usage["max_storage"]
            storage_pct = (usage["total_storage"] / max_storage * 100) if max_storage > 0 else 0.0
            read_limit = usage["daily_rows_read_limit"]
            read_pct = (usage["daily_rows_read"] / read_limit * 100) if read_limit > 0 else 0.0
            write_limit = usage["daily_rows_written_limit"]
            write_pct = (
                (usage["daily_rows_written"] / write_limit * 100) if write_limit > 0 else 0.0
            )

            results.append(
                create_metric(
                    global_resource,
                    "storage_usage_percent",
                    storage_pct,
                    "Percent",
                    "gauge",
                    "now",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "rows_read_usage_percent",
                    read_pct,
                    "Percent",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "rows_written_usage_percent",
                    write_pct,
                    "Percent",
                    "gauge",
                    "today",
                    paid_meta,
                )
            )

        # Fetch per-database analytics for the configured timeframe
        if db_resources:
            analytics_data = self.client.fetch_d1_analytics(db_ids, timeframe)

            for resource in db_resources:
                version = resource.metadata.get("version", "unknown")
                file_size = file_sizes.get(resource.id, 0)

                analytics = analytics_data.get(resource.id, {})

                # Status: 1 = database exists and is accessible
                results.append(
                    create_metric(
                        resource,
                        "status",
                        1.0,
                        "Status",
                        "gauge",
                        timeframe,
                        extra_metadata={
                            "version": version,
                            "created_at": resource.metadata.get("created_at"),
                        },
                    )
                )

                # Storage Size (from REST API metadata)
                results.append(
                    create_metric(
                        resource,
                        "storage_bytes",
                        float(file_size),
                        "Storage Size",
                        "gauge",
                        timeframe,
                    )
                )

                # Analytics Metrics
                results.append(
                    create_metric(
                        resource,
                        "query_count",
                        float(analytics.get("query_count", 0)),
                        "Query Count",
                        "sum",
                        timeframe,
                    )
                )

                results.append(
                    create_metric(
                        resource,
                        "read_rows",
                        float(analytics.get("read_rows", 0)),
                        "Rows Read",
                        "sum",
                        timeframe,
                    )
                )

                results.append(
                    create_metric(
                        resource,
                        "write_rows",
                        float(analytics.get("write_rows", 0)),
                        "Rows Written",
                        "sum",
                        timeframe,
                    )
                )

                results.append(
                    create_metric(
                        resource,
                        "duration_avg",
                        float(analytics.get("duration_avg", 0)),
                        "Avg Duration",
                        "gauge",
                        timeframe,
                    )
                )

        return results
