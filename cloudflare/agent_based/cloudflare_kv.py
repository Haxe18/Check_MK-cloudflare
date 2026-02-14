#!/usr/bin/env python3
"""Cloudflare KV Namespaces check plugin."""

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
    SERVICE_KV,
    check_usage_limit,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_bytes,
    format_count,
    get_resource_id_by_name,
)

# Special resource ID for account-wide usage
USAGE_RESOURCE_ID = "_kv_usage"


def discover_cloudflare_kv(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare KV Namespaces.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered KV namespace
    """
    for resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_KV):
        # Skip global resource - handled by separate check
        if resource_id == USAGE_RESOURCE_ID:
            continue
        yield Service(item=resource_name)


def discover_cloudflare_kv_global(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare KV Global service.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for KV global stats if found
    """
    for resource_id, _resource_name in discover_cloudflare_resources_by_name(section, SERVICE_KV):
        if resource_id == USAGE_RESOURCE_ID:
            yield Service()  # No item - service_name has no %s
            return


def check_cloudflare_kv(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check a Cloudflare KV Namespace.

    Args:
        item: Namespace name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_KV, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="KV namespace not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_KV, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="KV namespace not found in data")
        return

    # Extract metric values
    reads = metrics.get("reads", {}).get("value", 0)
    writes = metrics.get("writes", {}).get("value", 0)
    deletes = metrics.get("deletes", {}).get("value", 0)
    lists = metrics.get("lists", {}).get("value", 0)
    key_count = metrics.get("key_count", {}).get("value", 0)
    storage_bytes = metrics.get("storage_bytes", {}).get("value", 0)

    # Latency quantiles (matching Cloudflare dashboard: P50, P75, P90, P99)
    latency_p50 = metrics.get("latency_p50", {}).get("value", 0)
    latency_p75 = metrics.get("latency_p75", {}).get("value", 0)
    latency_p90 = metrics.get("latency_p90", {}).get("value", 0)
    latency_p99 = metrics.get("latency_p99", {}).get("value", 0)

    # Read status (hot/cold/not_found)
    hot_reads = metrics.get("hot_reads", {}).get("value", 0)
    cold_reads = metrics.get("cold_reads", {}).get("value", 0)
    not_found = metrics.get("not_found", {}).get("value", 0)

    # Monthly summary
    reads_month = metrics.get("reads_month", {}).get("value", 0)
    writes_month = metrics.get("writes_month", {}).get("value", 0)
    lists_month = metrics.get("lists_month", {}).get("value", 0)
    deletes_month = metrics.get("deletes_month", {}).get("value", 0)

    # Build summary - item is already the human-readable name
    summary_parts = [
        f"Keys: {format_count(key_count)}",
        f"Storage: {format_bytes(storage_bytes)}",
        f"Reads: {format_count(reads)}",
        f"Writes: {format_count(writes)}",
    ]

    if latency_p50 > 0:
        summary_parts.append(f"Latency P50: {latency_p50:.1f}ms")

    # Check key_count against thresholds (upper AND lower)
    key_count_upper = extract_levels(params, "key_count_levels")
    key_count_lower = extract_levels(params, "key_count_levels_lower")

    yield from check_levels(
        key_count,
        levels_upper=key_count_upper,
        levels_lower=key_count_lower,
        metric_name="cloudflare_kv_keys",
        label="Keys",
        render_func=format_count,
    )

    # Check reads/writes against thresholds
    yield from check_levels(
        reads,
        levels_upper=extract_levels(params, "reads_levels"),
        metric_name="cloudflare_kv_reads",
        label="Reads",
        render_func=format_count,
    )

    yield from check_levels(
        writes,
        levels_upper=extract_levels(params, "writes_levels"),
        metric_name="cloudflare_kv_writes",
        label="Writes",
        render_func=format_count,
    )

    # Check storage usage against thresholds
    yield from check_levels(
        storage_bytes,
        levels_upper=extract_levels(params, "storage_levels"),
        metric_name="cloudflare_kv_storage",
        label="Storage",
        render_func=format_bytes,
    )

    # Build summary (only if no threshold alerts)
    yield Result(state=State.OK, summary=", ".join(summary_parts))

    # Yield metrics (others)
    yield Metric("cloudflare_kv_deletes", deletes)
    yield Metric("cloudflare_kv_lists", lists)

    # Latency quantiles (always output for continuous graphs)
    yield Metric("cloudflare_kv_latency_p50", latency_p50)
    yield Metric("cloudflare_kv_latency_p75", latency_p75)
    yield Metric("cloudflare_kv_latency_p90", latency_p90)
    yield Metric("cloudflare_kv_latency_p99", latency_p99)

    # Read status (hot/cold/not_found)
    yield Metric("cloudflare_kv_hot_reads", hot_reads)
    yield Metric("cloudflare_kv_cold_reads", cold_reads)
    yield Metric("cloudflare_kv_not_found", not_found)

    # Monthly summary
    yield Metric("cloudflare_kv_reads_month", reads_month)
    yield Metric("cloudflare_kv_writes_month", writes_month)
    yield Metric("cloudflare_kv_lists_month", lists_month)
    yield Metric("cloudflare_kv_deletes_month", deletes_month)


check_plugin_cloudflare_kv = CheckPlugin(
    name="cloudflare_kv",
    sections=["cloudflare"],
    service_name="Cloudflare KV %s",
    discovery_function=discover_cloudflare_kv,
    check_function=check_cloudflare_kv,
    check_ruleset_name="cloudflare_kv",
    check_default_parameters={},
)


def check_cloudflare_kv_global(
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare KV Global stats (usage vs limits).

    Args:
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    metrics = collect_metrics_for_resource(section, SERVICE_KV, USAGE_RESOURCE_ID)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="KV usage data not found")
        return

    is_paid = metrics.get("daily_reads", {}).get("metadata", {}).get("is_paid_plan", False)
    plan_label = "Paid (usage-based)" if is_paid else "Free"
    free_tier_monitoring = params.get("free_tier_monitoring", True)
    total_ns = int(metrics.get("total_namespaces", {}).get("value", 0))

    # --- Namespaces (simple display) ---
    yield Result(state=State.OK, summary=f"Namespaces: {total_ns} ({plan_label})")
    yield Metric("cloudflare_kv_total_namespaces", total_ns)

    # --- Reads ---
    yield from check_usage_limit(
        usage=int(metrics.get("daily_reads", {}).get("value", 0)),
        limit=int(metrics.get("reads_limit", {}).get("value", 0)),
        label="Reads",
        metric_usage="cloudflare_kv_daily_reads",
        metric_limit="cloudflare_kv_reads_limit",
        metric_percent="cloudflare_kv_reads_usage_percent",
        params=params,
        param_key="reads_usage_levels",
        free_tier_monitoring=free_tier_monitoring,
    )

    # --- Writes ---
    yield from check_usage_limit(
        usage=int(metrics.get("daily_writes", {}).get("value", 0)),
        limit=int(metrics.get("writes_limit", {}).get("value", 0)),
        label="Writes",
        metric_usage="cloudflare_kv_daily_writes",
        metric_limit="cloudflare_kv_writes_limit",
        metric_percent="cloudflare_kv_writes_usage_percent",
        params=params,
        param_key="writes_usage_levels",
        free_tier_monitoring=free_tier_monitoring,
    )

    # --- Deletes ---
    yield from check_usage_limit(
        usage=int(metrics.get("daily_deletes", {}).get("value", 0)),
        limit=int(metrics.get("deletes_limit", {}).get("value", 0)),
        label="Deletes",
        metric_usage="cloudflare_kv_daily_deletes",
        metric_limit="cloudflare_kv_deletes_limit",
        metric_percent="cloudflare_kv_deletes_usage_percent",
        params=params,
        param_key="deletes_usage_levels",
        free_tier_monitoring=free_tier_monitoring,
    )

    # --- Lists ---
    yield from check_usage_limit(
        usage=int(metrics.get("daily_lists", {}).get("value", 0)),
        limit=int(metrics.get("lists_limit", {}).get("value", 0)),
        label="Lists",
        metric_usage="cloudflare_kv_daily_lists",
        metric_limit="cloudflare_kv_lists_limit",
        metric_percent="cloudflare_kv_lists_usage_percent",
        params=params,
        param_key="lists_usage_levels",
        free_tier_monitoring=free_tier_monitoring,
    )


check_plugin_cloudflare_kv_global = CheckPlugin(
    name="cloudflare_kv_global",
    sections=["cloudflare"],
    service_name="Cloudflare KV Global",
    discovery_function=discover_cloudflare_kv_global,
    check_function=check_cloudflare_kv_global,
    check_ruleset_name="cloudflare_kv_global",
    check_default_parameters={"free_tier_monitoring": True},
)
