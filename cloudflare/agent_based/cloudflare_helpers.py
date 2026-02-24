#!/usr/bin/env python3
"""Shared helper utilities for Cloudflare check plugins."""

from collections.abc import Callable, Generator
from typing import Any

from cmk.agent_based.v2 import CheckResult, Metric, Result, State

from ..lib import constants as lib_constants

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


def parse_fixed_levels(
    levels: Any,
    default_warn: float,
    default_crit: float,
) -> tuple[float, float] | None:
    """Parse SimpleLevels params (Checkmk v2 format) into fixed warn/crit values.

    Args:
        levels: Raw levels value from params: ("fixed", (warn, crit)),
            ("no_levels", None), or None if the rule does not set it
        default_warn: Fallback warning threshold
        default_crit: Fallback critical threshold

    Returns:
        Tuple of (warn, crit) as floats, or None if levels are switched off
    """
    if not _is_valid_check_levels_param(levels):
        return default_warn, default_crit

    level_type, level_values = levels
    if level_type == "no_levels":
        return None
    if level_type == "fixed":
        return float(level_values[0]), float(level_values[1])

    return default_warn, default_crit


def usage_state(pct: float, levels: tuple[float, float] | None) -> State:
    """Map a usage percentage to a check state.

    Args:
        pct: Usage in percent of the limit
        levels: (warn, crit) percentages, or None if levels are switched off

    Returns:
        State.CRIT/WARN when the matching level is reached, otherwise State.OK
    """
    if levels is None:
        return State.OK
    warn_pct, crit_pct = levels
    if pct >= crit_pct:
        return State.CRIT
    if pct >= warn_pct:
        return State.WARN
    return State.OK


def _is_valid_check_levels_param(levels: Any) -> bool:
    """Validate Checkmk v2 check_levels parameter format.

    Supported formats:
    - ("fixed", (warn, crit))
    - ("no_levels", None)
    - ("predictive", <payload>)  # payload validated by Checkmk
    """
    if not isinstance(levels, tuple) or len(levels) != 2:
        return False

    mode, payload = levels
    if not isinstance(mode, str):
        return False

    if mode == "fixed":
        return (
            isinstance(payload, tuple)
            and len(payload) == 2
            and all(isinstance(v, (int, float)) for v in payload)
        )

    if mode == "no_levels":
        return payload is None

    if mode == "predictive":
        return True

    return False


def extract_levels(params: dict[str, Any], param_key: str) -> tuple[str, Any] | None:
    """Extract threshold levels from params in Checkmk v2 format.

    Args:
        params: Check parameters with threshold configuration
        param_key: Key for threshold in params

    Returns:
        Checkmk v2 levels tuple or None if not configured/invalid
    """
    levels = params.get(param_key)
    if levels is None:
        return None
    return levels if _is_valid_check_levels_param(levels) else None


def get_metric_data(metrics: dict[str, Any], metric_name: str) -> dict[str, Any]:
    """Return a metric payload as dict, or an empty dict if invalid/missing.

    Args:
        metrics: Metric mapping for one resource
        metric_name: Metric key to retrieve

    Returns:
        Metric payload dictionary
    """
    metric = metrics.get(metric_name, {})
    return metric if isinstance(metric, dict) else {}


def metric_float(metrics: dict[str, Any], metric_name: str, default: float = 0.0) -> float:
    """Read a metric value as float with a safe fallback.

    Args:
        metrics: Metric mapping for one resource
        metric_name: Metric key to retrieve
        default: Fallback value if conversion fails

    Returns:
        Metric value as float
    """
    value = get_metric_data(metrics, metric_name).get("value", default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def metric_int(metrics: dict[str, Any], metric_name: str, default: int = 0) -> int:
    """Read a metric value as int with a safe fallback.

    Args:
        metrics: Metric mapping for one resource
        metric_name: Metric key to retrieve
        default: Fallback value if conversion fails

    Returns:
        Metric value as int
    """
    return int(metric_float(metrics, metric_name, float(default)))


def metric_metadata(metrics: dict[str, Any], metric_name: str) -> dict[str, Any]:
    """Read metric metadata as dict with safe fallback.

    Args:
        metrics: Metric mapping for one resource
        metric_name: Metric key to retrieve metadata from

    Returns:
        Metadata dictionary
    """
    metadata = get_metric_data(metrics, metric_name).get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


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

    # Extract threshold levels (None = levels switched off in the rule)
    levels = parse_fixed_levels(params.get(param_key), default_warn, default_crit)
    if not free_tier_monitoring or limit <= 0:
        levels = None

    state = usage_state(pct, levels)

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
        levels=levels,
    )
