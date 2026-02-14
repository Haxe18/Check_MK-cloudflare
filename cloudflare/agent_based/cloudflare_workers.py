#!/usr/bin/env python3
"""Cloudflare Workers check plugin."""

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
    FREE_PLAN_DAILY_LIMIT,
    SERVICE_WORKERS,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_count,
    get_resource_id_by_name,
)

# Special resource ID for account-wide usage
USAGE_RESOURCE_ID = "_workers_usage"


def discover_cloudflare_workers(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Workers.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered worker
    """
    for resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_WORKERS
    ):
        # Skip global resource - handled by separate check
        if resource_id == USAGE_RESOURCE_ID:
            continue
        yield Service(item=resource_name)


def discover_cloudflare_workers_global(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Workers Global service.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for workers global stats if found
    """
    for resource_id, _resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_WORKERS
    ):
        if resource_id == USAGE_RESOURCE_ID:
            yield Service()  # No item - service_name has no %s
            return


def check_cloudflare_workers(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check a Cloudflare Worker.

    Args:
        item: Worker name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_WORKERS, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Worker not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_WORKERS, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Worker not found in data")
        return

    # Extract metric values
    requests = metrics.get("requests", {}).get("value", 0)
    errors = metrics.get("errors", {}).get("value", 0)
    daily_requests = metrics.get("daily_requests", {}).get("value", 0)

    # CPU Time quantiles
    cpu_p50 = metrics.get("cpu_time_p50", {}).get("value", 0)
    cpu_p90 = metrics.get("cpu_time_p90", {}).get("value", 0)
    cpu_p99 = metrics.get("cpu_time_p99", {}).get("value", 0)
    cpu_p999 = metrics.get("cpu_time_p999", {}).get("value", 0)

    # Wall Time quantiles
    wall_p50 = metrics.get("wall_time_p50", {}).get("value", 0)
    wall_p90 = metrics.get("wall_time_p90", {}).get("value", 0)
    wall_p99 = metrics.get("wall_time_p99", {}).get("value", 0)
    wall_p999 = metrics.get("wall_time_p999", {}).get("value", 0)

    # Duration quantiles
    duration_p50 = metrics.get("duration_p50", {}).get("value", 0)
    duration_p90 = metrics.get("duration_p90", {}).get("value", 0)
    duration_p99 = metrics.get("duration_p99", {}).get("value", 0)
    duration_p999 = metrics.get("duration_p999", {}).get("value", 0)

    # Calculate error rate
    error_rate = (errors / requests * 100) if requests > 0 else 0

    # 1. Requests (Check + Metric)
    # Always check/show requests
    requests_levels = extract_levels(params, "requests_levels")
    yield from check_levels(
        requests,
        levels_upper=requests_levels,
        metric_name="cloudflare_worker_requests",
        label="Requests",
        render_func=format_count,
    )

    # 2. Daily Requests (Metric only)
    yield Metric("cloudflare_worker_requests_today", daily_requests)

    # 3. Errors (Check + Metric)
    errors_levels = extract_levels(params, "errors_levels")
    if errors > 0 or errors_levels:
        yield from check_levels(
            errors,
            levels_upper=errors_levels,
            metric_name="cloudflare_worker_errors",
            label="Errors",
            render_func=format_count,
        )
    else:
        # Ensure metric exists for graph even if 0 and no threshold
        yield Metric("cloudflare_worker_errors", errors)

    # 4. Error Rate (Check + Metric)
    error_rate_levels = extract_levels(params, "error_rate_levels")
    if errors > 0 or error_rate_levels:
        yield from check_levels(
            error_rate,
            levels_upper=error_rate_levels,
            metric_name="cloudflare_worker_error_rate",
            label="Error Rate",
            render_func=lambda v: f"{v:.1f}%",
        )
    else:
        yield Metric("cloudflare_worker_error_rate", error_rate)

    # Timing metrics configuration
    # (Label, Value, Ruleset Key, Metric Name)
    timings_config = [
        # CPU Time
        ("CPU P50", cpu_p50, "cpu_time_p50_levels", "cloudflare_worker_cpu_p50"),
        ("CPU P90", cpu_p90, "cpu_time_p90_levels", "cloudflare_worker_cpu_p90"),
        ("CPU P99", cpu_p99, "cpu_time_p99_levels", "cloudflare_worker_cpu_p99"),
        ("CPU P999", cpu_p999, "cpu_time_p999_levels", "cloudflare_worker_cpu_p999"),
        # Wall Time
        ("Wall P50", wall_p50, "wall_time_p50_levels", "cloudflare_worker_wall_p50"),
        ("Wall P90", wall_p90, "wall_time_p90_levels", "cloudflare_worker_wall_p90"),
        ("Wall P99", wall_p99, "wall_time_p99_levels", "cloudflare_worker_wall_p99"),
        ("Wall P999", wall_p999, "wall_time_p999_levels", "cloudflare_worker_wall_p999"),
        # Request Duration
        ("Duration P50", duration_p50, "duration_p50_levels", "cloudflare_worker_duration_p50"),
        ("Duration P90", duration_p90, "duration_p90_levels", "cloudflare_worker_duration_p90"),
        ("Duration P99", duration_p99, "duration_p99_levels", "cloudflare_worker_duration_p99"),
        ("Duration P999", duration_p999, "duration_p999_levels", "cloudflare_worker_duration_p999"),
    ]

    for label, value, key, metric_name in timings_config:
        levels = extract_levels(params, key)
        # Always show text for P50s (to match previous behavior), or if thresholds are configured
        if levels or "P50" in label:
            yield from check_levels(
                value,
                levels_upper=levels,
                metric_name=metric_name,
                label=label,
                render_func=lambda v: f"{v:.2f}ms",
            )
        else:
            # Just metric, no text
            yield Metric(metric_name, value)


def check_cloudflare_workers_global(
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare Workers global stats (daily + monthly).

    Args:
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    metrics = collect_metrics_for_resource(section, SERVICE_WORKERS, USAGE_RESOURCE_ID)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Workers usage data not found")
        return

    # Extract metric values
    daily_requests = int(metrics.get("daily_requests", {}).get("value", 0))
    daily_limit = int(metrics.get("daily_limit", {}).get("value", FREE_PLAN_DAILY_LIMIT))
    usage_percent = metrics.get("daily_usage_percent", {}).get("value", 0)
    is_paid = metrics.get("daily_requests", {}).get("metadata", {}).get("is_paid_plan", False)

    # Extract monthly metrics
    monthly_requests = int(metrics.get("monthly_requests", {}).get("value", 0))
    free_tier_monitoring = params.get("free_tier_monitoring", True)

    # Determine state based on usage percentage
    state = State.OK
    warn_pct, crit_pct = 80.0, 95.0  # defaults

    # Parse daily_usage_levels (SimpleLevels format)
    daily_usage_levels = params.get("daily_usage_levels")
    if daily_usage_levels:
        if isinstance(daily_usage_levels, tuple):
            warn_pct, crit_pct = daily_usage_levels
        elif isinstance(daily_usage_levels, dict) and daily_usage_levels.get("type") == "fixed":
            warn_pct, crit_pct = daily_usage_levels.get("value", (80.0, 95.0))

    # Only check thresholds for free plan
    if free_tier_monitoring and not is_paid and daily_limit > 0:
        if usage_percent >= crit_pct:
            state = State.CRIT
        elif usage_percent >= warn_pct:
            state = State.WARN

    # Build summary with monthly data
    if is_paid or daily_limit == 0:
        summary = (
            f"Requests today: {format_count(daily_requests)} (Paid, usage-based), "
            f"Month: {format_count(monthly_requests)}"
        )
    else:
        summary = (
            f"Requests today: {format_count(daily_requests)}/"
            f"{format_count(daily_limit)} ({usage_percent:.1f}%"
            f"{'' if free_tier_monitoring else ', free-tier monitoring disabled'}), "
            f"Month: {format_count(monthly_requests)}"
        )

    yield Result(state=state, summary=summary)

    # Yield metrics with crit boundary for free plan limit line in graph
    if is_paid or daily_limit == 0:
        # Paid plan - no limit line
        yield Metric("cloudflare_workers_requests_today", daily_requests)
        yield Metric("cloudflare_workers_daily_limit", 0)
    else:
        # Free plan - add crit boundary at limit for red line in graph
        yield Metric(
            "cloudflare_workers_requests_today",
            daily_requests,
            boundaries=(0, daily_limit),
        )
        yield Metric(
            "cloudflare_workers_daily_limit",
            daily_limit,
            levels=(daily_limit, daily_limit),  # Warn=Crit=Limit for red line
        )

    yield Metric(
        "cloudflare_workers_usage_percent",
        usage_percent,
        levels=(warn_pct, crit_pct) if free_tier_monitoring and not is_paid else None,
    )

    # Monthly metrics
    yield Metric("cloudflare_workers_requests_month", monthly_requests)

    # Per-worker breakdown for stacked graph (Top 5 + Other)
    worker_breakdown = []
    for i in range(1, 6):
        slot_metric = metrics.get(f"top{i}_requests", {})
        slot_value = int(slot_metric.get("value", 0))
        slot_name = slot_metric.get("metadata", {}).get("worker_name", "")

        yield Metric(f"cloudflare_workers_top{i}_requests", slot_value)

        if slot_name and slot_value > 0:
            worker_breakdown.append(f"#{i}: {slot_name} ({format_count(slot_value)})")

    other_metric = metrics.get("other_requests", {})
    other_value = int(other_metric.get("value", 0))
    other_count = other_metric.get("metadata", {}).get("count", 0)

    yield Metric("cloudflare_workers_other_requests", other_value)

    # Add breakdown details to check output
    if worker_breakdown:
        details = "Top workers: " + ", ".join(worker_breakdown)
        if other_count > 0:
            details += f", Other ({other_count} workers): {format_count(other_value)}"
        yield Result(state=State.OK, notice=details)


check_plugin_cloudflare_workers = CheckPlugin(
    name="cloudflare_workers",
    sections=["cloudflare"],
    service_name="Cloudflare Worker %s",
    discovery_function=discover_cloudflare_workers,
    check_function=check_cloudflare_workers,
    check_ruleset_name="cloudflare_workers",
    check_default_parameters={},
)


check_plugin_cloudflare_workers_global = CheckPlugin(
    name="cloudflare_workers_global",
    sections=["cloudflare"],
    service_name="Cloudflare Workers Global",
    discovery_function=discover_cloudflare_workers_global,
    check_function=check_cloudflare_workers_global,
    check_ruleset_name="cloudflare_workers_global",
    check_default_parameters={"free_tier_monitoring": True},
)
