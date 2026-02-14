#!/usr/bin/env python3
"""Cloudflare R2 Buckets check plugin."""

from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    check_levels,
)

from .cloudflare_helpers import (
    SERVICE_R2,
    check_usage_limit,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_bytes,
    format_count,
    get_resource_id_by_name,
    get_resource_metadata,
)

# Special resource ID for account-wide usage
USAGE_RESOURCE_ID = "_r2_usage"


def discover_cloudflare_r2(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare R2 Buckets.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered R2 bucket
    """
    for resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_R2):
        # Skip global resource - handled by separate check
        if resource_id == USAGE_RESOURCE_ID:
            continue
        yield Service(item=resource_name)


def discover_cloudflare_r2_global(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare R2 Global service.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for R2 global stats if found
    """
    for resource_id, _resource_name in discover_cloudflare_resources_by_name(section, SERVICE_R2):
        if resource_id == USAGE_RESOURCE_ID:
            yield Service()  # No item - service_name has no %s
            return


def check_cloudflare_r2(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check a Cloudflare R2 Bucket.

    Args:
        item: Bucket name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_R2, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="R2 bucket not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_R2, resource_id)
    metadata = get_resource_metadata(section, SERVICE_R2, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="R2 bucket not found in data")
        return

    # Get bucket info
    location = metadata.get("location", "unknown")

    # Extract metric values
    storage_bytes = metrics.get("storage_bytes", {}).get("value", 0)
    object_count = int(metrics.get("object_count", {}).get("value", 0))

    # Check thresholds
    yield from check_levels(
        storage_bytes,
        levels_upper=extract_levels(params, "storage_levels"),
        metric_name="cloudflare_r2_storage",
        label="Storage",
        render_func=format_bytes,
    )

    yield from check_levels(
        object_count,
        levels_upper=extract_levels(params, "object_count_levels"),
        metric_name="cloudflare_r2_objects",
        label="Objects",
        render_func=format_count,
    )

    # Build summary
    summary_parts = [
        f"Location: {location}",
        f"Storage: {format_bytes(storage_bytes)}",
        f"Objects: {format_count(object_count)}",
    ]

    yield Result(state=State.OK, summary=", ".join(summary_parts))


check_plugin_cloudflare_r2 = CheckPlugin(
    name="cloudflare_r2",
    sections=["cloudflare"],
    service_name="Cloudflare R2 %s",
    discovery_function=discover_cloudflare_r2,
    check_function=check_cloudflare_r2,
    check_ruleset_name="cloudflare_r2",
    check_default_parameters={},
)


def check_cloudflare_r2_global(
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare R2 Global stats (usage vs included free tier).

    Args:
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    metrics = collect_metrics_for_resource(section, SERVICE_R2, USAGE_RESOURCE_ID)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="R2 usage data not found")
        return

    total_buckets = int(metrics.get("total_buckets", {}).get("value", 0))
    total_objects = int(metrics.get("total_objects", {}).get("value", 0))
    free_tier_monitoring = params.get("free_tier_monitoring", True)

    # --- Buckets & Objects (simple display) ---
    yield Result(
        state=State.OK, summary=f"Buckets: {total_buckets}, Objects: {format_count(total_objects)}"
    )
    yield Metric("cloudflare_r2_total_buckets", total_buckets)
    yield Metric("cloudflare_r2_total_objects", total_objects)

    # --- Storage ---
    storage_usage = float(metrics.get("total_storage", {}).get("value", 0))
    included_free_tier = float(metrics.get("max_storage", {}).get("value", 0))

    if free_tier_monitoring:
        yield from check_usage_limit(
            usage=storage_usage,
            limit=included_free_tier,
            label="Storage (Included Free Tier)",
            metric_usage="cloudflare_r2_total_storage",
            metric_limit="cloudflare_r2_max_storage",
            metric_percent="cloudflare_r2_storage_usage_percent",
            params=params,
            param_key="storage_usage_levels",
            render_func=format_bytes,
            free_tier_monitoring=free_tier_monitoring,
        )
    else:
        usage_pct = (storage_usage / included_free_tier * 100) if included_free_tier > 0 else 0.0
        yield Result(
            state=State.OK,
            summary=(
                f"Storage (Included Free Tier): {format_bytes(storage_usage)}/"
                f"{format_bytes(included_free_tier)} ({usage_pct:.1f}%, free-tier monitoring disabled)"
            ),
        )
        yield Metric(
            "cloudflare_r2_total_storage",
            storage_usage,
            boundaries=(0, included_free_tier) if included_free_tier > 0 else None,
        )
        yield Metric("cloudflare_r2_max_storage", included_free_tier)
        yield Metric("cloudflare_r2_storage_usage_percent", usage_pct)


check_plugin_cloudflare_r2_global = CheckPlugin(
    name="cloudflare_r2_global",
    sections=["cloudflare"],
    service_name="Cloudflare R2 Global",
    discovery_function=discover_cloudflare_r2_global,
    check_function=check_cloudflare_r2_global,
    check_ruleset_name="cloudflare_r2_global",
    check_default_parameters={"free_tier_monitoring": True},
)
