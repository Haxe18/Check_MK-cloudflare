#!/usr/bin/env python3
"""R2 Buckets section for Cloudflare monitoring."""

from ..base import CloudflareSection
from ..constants import R2_JURISDICTIONS
from ..types import MetricDefinition, MetricResult, Resource, create_metric


class R2Section(CloudflareSection):
    """Section for Cloudflare R2 Buckets monitoring."""

    # Special resource ID for account-wide global stats
    USAGE_RESOURCE_ID = "_r2_usage"

    @property
    def name(self) -> str:
        """Return the service identifier.

        Returns:
            str: Service name key.
        """
        return "r2"

    @property
    def resource_type(self) -> str:
        """Return the default per-item resource type.

        Returns:
            str: Resource type for R2 bucket items.
        """
        return "r2_bucket"

    @property
    def metrics(self) -> list[MetricDefinition]:
        """Return metric definitions collected for this service.

        Returns:
            list[MetricDefinition]: Metrics for R2 checks.
        """
        return [
            MetricDefinition("location", "gauge", "Status"),
            MetricDefinition("storage_bytes", "gauge", "Storage Bytes"),
            MetricDefinition("object_count", "gauge", "Object Count"),
        ]

    def discover_resources(self) -> list[Resource]:
        """Discover all R2 buckets.

        Returns:
            List of R2 bucket resources
        """
        resources = []
        # Keep track of found buckets to avoid duplicates (shouldn't happen but good for safety)
        found_buckets = set()

        for jurisdiction in R2_JURISDICTIONS:
            try:
                buckets = self.client.list_r2_buckets(jurisdiction=jurisdiction)

                for bucket in buckets:
                    bucket_name = bucket.get("name")
                    if not bucket_name or bucket_name in found_buckets:
                        continue

                    found_buckets.add(bucket_name)

                    # Determine location/region
                    # 1. Try explicit 'location' field
                    # 2. Try 'locationHint' field (seen in some API versions)
                    # 3. Fallback to jurisdiction name if available
                    # 4. Fallback to "Global" (standard for R2)
                    location = bucket.get("location")
                    if not location:
                        location = bucket.get("locationHint")
                    if not location:
                        location = jurisdiction.upper() if jurisdiction else "Global"

                    resources.append(
                        Resource(
                            id=bucket_name,
                            name=bucket_name,
                            resource_type=self.resource_type,
                            metadata={
                                "location": location,
                                "created_on": bucket.get("creation_date"),
                                "jurisdiction": jurisdiction if jurisdiction else "default",
                            },
                            available_metrics=[m.name for m in self.metrics],
                        )
                    )
            except Exception as exc:
                self.client.log_warning(
                    f"Failed to list R2 buckets for jurisdiction {jurisdiction}: {exc}"
                )

        # Add special resource for account-wide global stats
        bucket_names = [r.name for r in resources]
        resources.insert(
            0,
            Resource(
                id=self.USAGE_RESOURCE_ID,
                name="R2 Global",
                resource_type="r2_global",
                metadata={"_bucket_names": bucket_names},
                available_metrics=[
                    "total_storage",
                    "max_storage",
                    "total_objects",
                    "total_buckets",
                ],
            ),
        )

        return resources

    def fetch_analytics(
        self,
        resources: list[Resource],
        timeframe: str,
    ) -> list[MetricResult]:
        """Fetch R2 bucket metrics.

        Args:
            resources: List of R2 bucket resources
            timeframe: Time range

        Returns:
            List of metric results
        """
        # Separate global resource from bucket resources
        global_resource = next((r for r in resources if r.id == self.USAGE_RESOURCE_ID), None)
        bucket_resources = [r for r in resources if r.id != self.USAGE_RESOURCE_ID]

        results: list[MetricResult] = []
        bucket_names = [r.name for r in bucket_resources]

        # Fetch analytics for all buckets
        analytics = self.client.fetch_r2_analytics(bucket_names, timeframe)

        # Fetch account-wide usage (aggregates from per-bucket analytics)
        if global_resource:
            usage = self.client.fetch_r2_account_usage(analytics)

            results.append(
                create_metric(
                    global_resource,
                    "total_storage",
                    float(usage.get("total_storage", 0)),
                    "Bytes",
                    "gauge",
                    "now",
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "max_storage",
                    float(usage.get("max_storage", 0)),
                    "Bytes",
                    "gauge",
                    "now",
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "total_objects",
                    float(usage.get("total_objects", 0)),
                    "Count",
                    "gauge",
                    "now",
                )
            )
            results.append(
                create_metric(
                    global_resource,
                    "total_buckets",
                    float(usage.get("total_buckets", 0)),
                    "Count",
                    "gauge",
                    "now",
                )
            )

        for resource in bucket_resources:
            location = resource.metadata.get("location", "unknown")

            # Location presence as status (1 = configured)
            results.append(
                create_metric(
                    resource,
                    "location",
                    1.0,
                    "Status",
                    "gauge",
                    timeframe,
                    extra_metadata={"location": location},
                )
            )

            # Get analytics for this bucket
            bucket_data = analytics.get(resource.name, {})

            # Storage Bytes
            results.append(
                create_metric(
                    resource,
                    "storage_bytes",
                    float(bucket_data.get("storage_bytes", 0)),
                    "Storage Bytes",
                    "gauge",
                    timeframe,
                )
            )

            # Object Count
            results.append(
                create_metric(
                    resource,
                    "object_count",
                    float(bucket_data.get("object_count", 0)),
                    "Object Count",
                    "gauge",
                    timeframe,
                )
            )

        return results
