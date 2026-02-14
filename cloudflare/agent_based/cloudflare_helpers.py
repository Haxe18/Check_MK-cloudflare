#!/usr/bin/env python3
"""Shared helper utilities for Cloudflare check plugins."""

from collections.abc import Callable, Generator
from typing import Any

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, check_levels

from ..lib import constants as lib_constants

DEFAULT_TIMEFRAME = lib_constants.DEFAULT_TIMEFRAME
FREE_PLAN_DAILY_LIMIT = lib_constants.FREE_PLAN_DAILY_LIMIT
SERVICE_ACCESS = lib_constants.SERVICE_ACCESS
SERVICE_D1 = lib_constants.SERVICE_D1
SERVICE_DNS_ANALYTICS = lib_constants.SERVICE_DNS_ANALYTICS
SERVICE_KV = lib_constants.SERVICE_KV
SERVICE_LOAD_BALANCER = lib_constants.SERVICE_LOAD_BALANCER
SERVICE_PAGES = lib_constants.SERVICE_PAGES
SERVICE_R2 = lib_constants.SERVICE_R2
SERVICE_RULESETS = lib_constants.SERVICE_RULESETS
SERVICE_SSL = lib_constants.SERVICE_SSL
SERVICE_TUNNEL = lib_constants.SERVICE_TUNNEL
SERVICE_WAF = lib_constants.SERVICE_WAF
SERVICE_WORKERS = lib_constants.SERVICE_WORKERS
SERVICE_ZONE_ANALYTICS = lib_constants.SERVICE_ZONE_ANALYTICS
SERVICE_ZONES = lib_constants.SERVICE_ZONES


def get_service_data(section: dict[str, Any], service: str) -> dict[str, Any] | None:
    """Get data for a specific service from the parsed section.

    Args:
        section: Parsed cloudflare section
        service: Service name (e.g., 'workers', 'kv')

    Returns:
        Service data or None if not found
    """
    metrics = section.get("CloudflareMetrics", {})
    return metrics.get(service)


def discover_cloudflare_resources_by_name(
    section: dict[str, Any],
    service: str,
) -> Generator[tuple[str, str], None, None]:
    """Discover resources for a Cloudflare service with names.

    Args:
        section: Parsed cloudflare section
        service: Service name

    Yields:
        Tuples of (resource_id, resource_name)
    """
    service_data = get_service_data(section, service)
    if not service_data:
        return

    resources = service_data.get("resources", [])
    for resource in resources:
        resource_id = resource.get("id")
        resource_name = resource.get("name", resource_id)
        if resource_id and resource_name:
            yield resource_id, resource_name


def get_resource_id_by_name(
    section: dict[str, Any],
    service: str,
    resource_name: str,
) -> str | None:
    """Find resource ID by name.

    Args:
        section: Parsed cloudflare section
        service: Service name
        resource_name: Resource name to look up

    Returns:
        Resource ID or None if not found
    """
    service_data = get_service_data(section, service)
    if not service_data:
        return None

    resources = service_data.get("resources", [])
    for resource in resources:
        if resource.get("name") == resource_name:
            return resource.get("id")

    return None


def collect_metrics_for_resource(
    section: dict[str, Any],
    service: str,
    resource_id: str,
) -> dict[str, Any]:
    """Collect all metrics for a specific resource.

    Args:
        section: Parsed cloudflare section
        service: Service name
        resource_id: Resource ID to collect metrics for

    Returns:
        Dictionary of metric name to metric data
    """
    service_data = get_service_data(section, service)
    if not service_data:
        return {}

    metrics_list = service_data.get("metrics", [])
    result: dict[str, Any] = {}

    for metric in metrics_list:
        if metric.get("resource_id") == resource_id:
            metric_name = metric.get("metric_name")
            if metric_name:
                result[metric_name] = metric

    return result


def get_resource_metadata(
    section: dict[str, Any],
    service: str,
    resource_id: str,
) -> dict[str, Any]:
    """Get metadata for a specific resource.

    Args:
        section: Parsed cloudflare section
        service: Service name
        resource_id: Resource ID

    Returns:
        Resource metadata dictionary
    """
    service_data = get_service_data(section, service)
    if not service_data:
        return {}

    resources = service_data.get("resources", [])
    for resource in resources:
        if resource.get("id") == resource_id:
            return resource.get("metadata", {})

    return {}


def get_timeframe(section: dict[str, Any], service: str) -> str:
    """Get the analytics timeframe for a service.

    Args:
        section: Parsed cloudflare section
        service: Service name

    Returns:
        Timeframe string (e.g., '24h')
    """
    service_data = get_service_data(section, service)
    if service_data:
        return service_data.get("timeframe", DEFAULT_TIMEFRAME)
    return DEFAULT_TIMEFRAME


def format_bytes(byte_count: float) -> str:
    """Format bytes to human-readable string.

    Args:
        byte_count: Number of bytes

    Returns:
        Formatted string (e.g., '1.5 GB')
    """
    if byte_count >= 1_000_000_000:
        return f"{byte_count / 1_000_000_000:.1f} GB"
    if byte_count >= 1_000_000:
        return f"{byte_count / 1_000_000:.1f} MB"
    if byte_count >= 1_000:
        return f"{byte_count / 1_000:.1f} KB"
    return f"{byte_count:.0f} B"


def format_count(count: float) -> str:
    """Format count with thousand separators.

    Args:
        count: Number to format

    Returns:
        Formatted string (e.g., '1,234,567')
    """
    return f"{int(count):,}"


def check_metric_levels(
    value: float,
    metric_name: str,
    params: dict[str, Any],
    param_key: str,
    label: str,
    render_func: Callable[[float], str] = str,
    boundaries: tuple[float | None, float | None] | None = None,
) -> CheckResult:
    """Check metric value against configured thresholds.

    Args:
        value: Metric value to check
        metric_name: Name for the metric output
        params: Check parameters with threshold configuration
        param_key: Key for threshold in params (e.g., 'error_rate_levels')
        label: Human-readable label for the metric
        render_func: Function to render the value
        boundaries: Optional (min, max) boundaries for the metric

    Yields:
        Check results and metrics
    """
    levels = params.get(param_key)

    # Handle SimpleLevels format
    levels_upper = None
    if levels is not None:
        if isinstance(levels, tuple) and len(levels) == 2:
            # Direct (warn, crit) tuple
            levels_upper = levels
        elif isinstance(levels, dict):
            # SimpleLevelsConfigModel format
            if levels.get("type") == "fixed":
                levels_upper = levels.get("value")

    yield from check_levels(
        value,
        levels_upper=levels_upper,
        metric_name=metric_name,
        label=label,
        render_func=render_func,
        boundaries=boundaries,
    )


def extract_levels(params: dict[str, Any], param_key: str) -> tuple[float, float] | None:
    """Extract threshold levels from params.

    Args:
        params: Check parameters with threshold configuration
        param_key: Key for threshold in params

    Returns:
        Tuple of (warn, crit) or None if not configured
    """
    levels = params.get(param_key)
    if levels is None:
        return None
    if isinstance(levels, tuple) and len(levels) == 2:
        return levels
    if isinstance(levels, dict) and levels.get("type") == "fixed":
        return levels.get("value")
    return None


def check_metric_levels_lower(
    value: float,
    metric_name: str,
    params: dict[str, Any],
    param_key: str,
    label: str,
    render_func: Callable[[float], str] = str,
    boundaries: tuple[float | None, float | None] | None = None,
) -> CheckResult:
    """Check metric value against lower thresholds.

    Args:
        value: Metric value to check
        metric_name: Name for the metric output
        params: Check parameters with threshold configuration
        param_key: Key for threshold in params
        label: Human-readable label for the metric
        render_func: Function to render the value
        boundaries: Optional (min, max) boundaries for the metric

    Yields:
        Check results and metrics
    """
    levels = params.get(param_key)

    # Handle SimpleLevels format
    levels_lower = None
    if levels is not None:
        if isinstance(levels, tuple) and len(levels) == 2:
            levels_lower = levels
        elif isinstance(levels, dict):
            if levels.get("type") == "fixed":
                levels_lower = levels.get("value")

    yield from check_levels(
        value,
        levels_lower=levels_lower,
        metric_name=metric_name,
        label=label,
        render_func=render_func,
        boundaries=boundaries,
    )


def check_usage_limit(
    usage: float,
    limit: float,
    label: str,
    metric_usage: str,
    metric_limit: str,
    metric_percent: str,
    params: dict[str, Any],
    param_key: str,
    render_func: Callable[[float], str] = format_count,
    default_warn: float = 80.0,
    default_crit: float = 95.0,
    free_tier_monitoring: bool = True,
) -> CheckResult:
    """Generic usage-vs-limit check with percentage thresholds.

    Calculates usage percentage, checks against configured thresholds,
    and yields Result + Metrics for usage, limit, and percentage.

    Args:
        usage: Current usage value
        limit: Plan limit value (0 = unlimited)
        label: Human-readable label (e.g., "Rows Read", "Storage")
        metric_usage: Metric name for usage value
        metric_limit: Metric name for limit value
        metric_percent: Metric name for usage percentage
        params: Check parameters with threshold configuration
        param_key: Key for percentage threshold in params
        render_func: Function to render usage/limit values
        default_warn: Default warning threshold percentage
        default_crit: Default critical threshold percentage
        free_tier_monitoring: Whether free-tier percentage evaluation should be applied

    Yields:
        Result with summary, Metric for usage, Metric for limit, Metric for percentage
    """
    # Calculate percentage
    pct = (usage / limit * 100) if limit > 0 else 0.0

    # Extract threshold levels
    warn_pct, crit_pct = default_warn, default_crit
    levels = params.get(param_key)
    if levels:
        if isinstance(levels, tuple):
            warn_pct, crit_pct = levels
        elif isinstance(levels, dict) and levels.get("type") == "fixed":
            warn_pct, crit_pct = levels.get("value", (default_warn, default_crit))

    # Determine state
    state = State.OK
    if free_tier_monitoring and limit > 0:
        if pct >= crit_pct:
            state = State.CRIT
        elif pct >= warn_pct:
            state = State.WARN

    # Summary text
    if limit > 0:
        yield Result(
            state=state,
            summary=(
                f"{label}: {render_func(usage)}/{render_func(limit)} ({pct:.1f}%)"
                if free_tier_monitoring
                else f"{label}: {render_func(usage)}/{render_func(limit)} "
                f"({pct:.1f}%, free-tier monitoring disabled)"
            ),
        )
    else:
        yield Result(
            state=state,
            summary=f"{label}: {render_func(usage)} (unlimited)",
        )

    # Usage metric with boundary at limit
    yield Metric(
        metric_usage,
        usage,
        boundaries=(0, limit) if limit > 0 else None,
    )

    # Limit metric
    yield Metric(metric_limit, limit)

    # Percentage metric with threshold levels
    yield Metric(
        metric_percent,
        pct,
        levels=(warn_pct, crit_pct) if free_tier_monitoring and limit > 0 else None,
    )
