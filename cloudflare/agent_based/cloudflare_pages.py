#!/usr/bin/env python3
"""Cloudflare Pages check plugin."""

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

from ..lib.constants import STATE_MAP
from .cloudflare_helpers import (
    SERVICE_PAGES,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_count,
    get_resource_id_by_name,
    get_resource_metadata,
)


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def discover_cloudflare_pages(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Pages projects.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered project
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_PAGES
    ):
        yield Service(item=resource_name)


def discover_cloudflare_pages_functions(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Pages projects with Functions.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each project with Functions enabled
    """
    for resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_PAGES):
        metadata = get_resource_metadata(section, SERVICE_PAGES, resource_id)
        if metadata.get("uses_functions", False):
            yield Service(item=resource_name)


def check_cloudflare_pages(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check a Cloudflare Pages project deployment status.

    Args:
        item: Project name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    resource_id = get_resource_id_by_name(section, SERVICE_PAGES, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Project not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_PAGES, resource_id)
    if not metrics:
        yield Result(state=State.UNKNOWN, summary="No metrics found")
        return

    # Extract deployment status
    deployment_status_metric = metrics.get("deployment_status", {})
    deployment_status = int(deployment_status_metric.get("value", 2))
    status_metadata = deployment_status_metric.get("metadata", {})
    status_text = status_metadata.get("status_text", "unknown")

    # Extract deployment age
    deployment_age = metrics.get("deployment_age_seconds", {}).get("value", 0)

    # Extract domains count
    domains_count_metric = metrics.get("domains_count", {})
    domains_count = int(domains_count_metric.get("value", 0))

    # Determine check state based on deployment status
    # 0 = success -> OK
    # 1 = building -> configurable (default OK)
    # 2 = failed -> CRIT
    state = State.OK
    if deployment_status == 2:
        state = State.CRIT
    elif deployment_status == 1:
        # Building state - check params
        building_state = params.get("building_state", "ok")
        state = State(STATE_MAP.get(building_state, 0))

    # Check deployment age threshold
    yield from check_levels(
        deployment_age,
        levels_upper=extract_levels(params, "max_deployment_age"),
        metric_name="cloudflare_pages_deployment_age",
        label="Deployment Age",
        render_func=_format_duration,
    )

    # Build summary
    summary_parts = [f"Status: {status_text}"]
    if deployment_age > 0:
        summary_parts.append(f"Age: {_format_duration(deployment_age)}")
    if domains_count > 0:
        summary_parts.append(f"Domains: {domains_count}")

    yield Result(state=state, summary=", ".join(summary_parts))


def check_cloudflare_pages_functions(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare Pages Functions analytics.

    Args:
        item: Project name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    resource_id = get_resource_id_by_name(section, SERVICE_PAGES, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Project not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_PAGES, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="No metrics found")
        return

    # Extract Functions metrics
    invocations = metrics.get("invocations", {}).get("value", 0)
    errors = metrics.get("errors", {}).get("value", 0)
    cpu_p50 = metrics.get("cpu_time_p50", {}).get("value", 0)
    cpu_p99 = metrics.get("cpu_time_p99", {}).get("value", 0)

    # Calculate error rate
    error_rate = (errors / invocations * 100) if invocations > 0 else 0

    # Check error rate threshold
    yield from check_levels(
        error_rate,
        levels_upper=extract_levels(params, "error_rate_levels"),
        metric_name="cloudflare_pages_functions_error_rate",
        label="Error Rate",
        render_func=lambda x: f"{x:.1f}%",
    )

    # Check CPU time thresholds
    yield from check_levels(
        cpu_p50,
        levels_upper=extract_levels(params, "cpu_time_p50_levels"),
        metric_name="cloudflare_pages_functions_cpu_p50",
        label="CPU Time P50",
        render_func=lambda x: f"{x:.2f}ms",
    )

    yield from check_levels(
        cpu_p99,
        levels_upper=extract_levels(params, "cpu_time_p99_levels"),
        metric_name="cloudflare_pages_functions_cpu_p99",
        label="CPU Time P99",
        render_func=lambda x: f"{x:.2f}ms",
    )

    # Build summary
    summary_parts = [f"Invocations: {format_count(invocations)}"]
    if errors > 0:
        summary_parts.append(f"Errors: {format_count(errors)} ({error_rate:.1f}%)")
    if cpu_p50 > 0:
        summary_parts.append(f"CPU P50: {cpu_p50:.2f}ms")

    yield Result(state=State.OK, summary=", ".join(summary_parts))

    # Yield metrics (always output for continuous graphs)
    yield Metric("cloudflare_pages_functions_invocations", invocations)
    yield Metric("cloudflare_pages_functions_errors", errors)


check_plugin_cloudflare_pages = CheckPlugin(
    name="cloudflare_pages",
    sections=["cloudflare"],
    service_name="Cloudflare Pages %s",
    discovery_function=discover_cloudflare_pages,
    check_function=check_cloudflare_pages,
    check_ruleset_name="cloudflare_pages",
    check_default_parameters={},
)


check_plugin_cloudflare_pages_functions = CheckPlugin(
    name="cloudflare_pages_functions",
    sections=["cloudflare"],
    service_name="Cloudflare Pages Functions %s",
    discovery_function=discover_cloudflare_pages_functions,
    check_function=check_cloudflare_pages_functions,
    check_ruleset_name="cloudflare_pages_functions",
    check_default_parameters={"error_rate_levels": ("fixed", (5.0, 10.0))},
)
