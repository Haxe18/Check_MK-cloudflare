#!/usr/bin/env python3
"""Cloudflare D1 Database check plugin."""

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
    render,
)

from .cloudflare_helpers import (
    SERVICE_D1,
    check_usage_limit,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_count,
    get_resource_id_by_name,
    get_resource_metadata,
)

# Special resource ID for account-wide usage
USAGE_RESOURCE_ID = "_d1_usage"


def discover_cloudflare_d1(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare D1 Databases.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered D1 database
    """
    for resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_D1):
        # Skip global resource - handled by separate check
        if resource_id == USAGE_RESOURCE_ID:
            continue
        yield Service(item=resource_name)


def discover_cloudflare_d1_global(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare D1 Global service.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for D1 global stats if found
    """
    for resource_id, _resource_name in discover_cloudflare_resources_by_name(section, SERVICE_D1):
        if resource_id == USAGE_RESOURCE_ID:
            yield Service()  # No item - service_name has no %s
            return


def check_cloudflare_d1(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check a Cloudflare D1 Database.

    Args:
        item: Database name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_D1, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="D1 database not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_D1, resource_id)
    metadata = get_resource_metadata(section, SERVICE_D1, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="D1 database not found in data")
        return

    # Get database info - item is already the name
    version = metadata.get("version", "unknown")
    created_at = metadata.get("created_at", "unknown")

    # Format created_at for display
    if created_at and created_at != "unknown":
        # Extract date part only
        created_date = created_at.split("T")[0] if "T" in created_at else created_at
    else:
        created_date = "unknown"

    yield Result(
        state=State.OK,
        summary=f"Version: {version}, Created: {created_date}",
    )

    # Yield status metric (1 = database exists)
    yield Metric("cloudflare_d1_status", 1)

    # Storage Size
    if (storage := metrics.get("storage_bytes")) is not None:
        yield from check_levels(
            storage.get("value"),
            levels_upper=extract_levels(params, "storage_levels"),
            metric_name="cloudflare_d1_storage",
            label="Storage",
            render_func=render.bytes,
        )

    # Query Count
    if (queries := metrics.get("query_count")) is not None:
        yield from check_levels(
            queries.get("value"),
            levels_upper=extract_levels(params, "query_count_levels"),
            metric_name="cloudflare_d1_queries",
            label="Queries",
            render_func=lambda v: f"{int(v)}",
        )

    # Rows Read
    if (read := metrics.get("read_rows")) is not None:
        yield Metric("cloudflare_d1_rows_read", read.get("value"))

    # Rows Written
    if (written := metrics.get("write_rows")) is not None:
        yield Metric("cloudflare_d1_rows_written", written.get("value"))

    # Avg Duration
    if (duration := metrics.get("duration_avg")) is not None:
        yield Metric("cloudflare_d1_duration_avg", duration.get("value"))


def check_cloudflare_d1_global(
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare D1 Global stats (usage vs limits).

    Args:
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    metrics = collect_metrics_for_resource(section, SERVICE_D1, USAGE_RESOURCE_ID)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="D1 usage data not found")
        return

    # Extract metric values
    total_databases = int(metrics.get("total_databases", {}).get("value", 0))
    max_databases = int(metrics.get("max_databases", {}).get("value", 0))
    is_paid = metrics.get("total_databases", {}).get("metadata", {}).get("is_paid_plan", False)
    plan_label = "Paid (usage-based)" if is_paid else "Free"
    free_tier_monitoring = params.get("free_tier_monitoring", True)

    # --- Databases (simple display, no threshold) ---
    yield Result(
        state=State.OK,
        summary=f"Databases: {total_databases}/{format_count(max_databases)} ({plan_label})",
    )
    yield Metric("cloudflare_d1_total_databases", total_databases)
    yield Metric("cloudflare_d1_max_databases", max_databases)

    # --- Storage ---
    yield from check_usage_limit(
        usage=metrics.get("total_storage", {}).get("value", 0),
        limit=metrics.get("max_storage", {}).get("value", 0),
        label="Storage",
        metric_usage="cloudflare_d1_total_storage",
        metric_limit="cloudflare_d1_max_storage",
        metric_percent="cloudflare_d1_storage_usage_percent",
        params=params,
        param_key="storage_usage_levels",
        render_func=render.bytes,
        free_tier_monitoring=free_tier_monitoring,
    )

    # --- Rows Read ---
    yield from check_usage_limit(
        usage=int(metrics.get("daily_rows_read", {}).get("value", 0)),
        limit=int(metrics.get("daily_rows_read_limit", {}).get("value", 0)),
        label="Rows read",
        metric_usage="cloudflare_d1_daily_rows_read",
        metric_limit="cloudflare_d1_daily_rows_read_limit",
        metric_percent="cloudflare_d1_rows_read_usage_percent",
        params=params,
        param_key="rows_read_usage_levels",
        free_tier_monitoring=free_tier_monitoring,
    )

    # --- Rows Written ---
    yield from check_usage_limit(
        usage=int(metrics.get("daily_rows_written", {}).get("value", 0)),
        limit=int(metrics.get("daily_rows_written_limit", {}).get("value", 0)),
        label="Rows written",
        metric_usage="cloudflare_d1_daily_rows_written",
        metric_limit="cloudflare_d1_daily_rows_written_limit",
        metric_percent="cloudflare_d1_rows_written_usage_percent",
        params=params,
        param_key="rows_written_usage_levels",
        free_tier_monitoring=free_tier_monitoring,
    )


check_plugin_cloudflare_d1 = CheckPlugin(
    name="cloudflare_d1",
    sections=["cloudflare"],
    service_name="Cloudflare D1 %s",
    discovery_function=discover_cloudflare_d1,
    check_function=check_cloudflare_d1,
    check_ruleset_name="cloudflare_d1",
    check_default_parameters={},
)


check_plugin_cloudflare_d1_global = CheckPlugin(
    name="cloudflare_d1_global",
    sections=["cloudflare"],
    service_name="Cloudflare D1 Global",
    discovery_function=discover_cloudflare_d1_global,
    check_function=check_cloudflare_d1_global,
    check_ruleset_name="cloudflare_d1_global",
    check_default_parameters={"free_tier_monitoring": True},
)
