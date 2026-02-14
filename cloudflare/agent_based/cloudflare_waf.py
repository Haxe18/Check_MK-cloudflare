#!/usr/bin/env python3
"""Cloudflare WAF check plugin."""

from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    check_levels,
)

from .cloudflare_helpers import (
    SERVICE_WAF,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_count,
    get_resource_id_by_name,
)


def discover_cloudflare_waf(section: dict[str, Any]) -> DiscoveryResult:
    """Discover zones for WAF monitoring.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered zone
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_WAF):
        yield Service(item=resource_name)


def check_cloudflare_waf(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check WAF Events.

    Args:
        item: Zone name (domain)
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_WAF, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="WAF data not found")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_WAF, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="WAF data not found")
        return

    # Extract metric values
    total_events = metrics.get("total_events", {}).get("value", 0)
    blocked_events = metrics.get("blocked_events", {}).get("value", 0)
    challenged_events = metrics.get("challenged_events", {}).get("value", 0)

    # Get plan from metadata
    metric_metadata = metrics.get("total_events", {}).get("metadata", {})
    plan = metric_metadata.get("plan", "")
    is_free_plan = "free" in plan.lower() if plan else False

    # Build summary - item is already the domain name in service name
    summary_parts = []

    if is_free_plan:
        summary_parts.append("Events: 0 (Free Plan - no data)")
    else:
        summary_parts.append(f"Events: {format_count(total_events)}")
        if blocked_events > 0:
            summary_parts.append(f"Blocked: {format_count(blocked_events)}")
        if challenged_events > 0:
            summary_parts.append(f"Challenged: {format_count(challenged_events)}")

    # Check total events threshold
    yield from check_levels(
        total_events,
        levels_upper=extract_levels(params, "total_events_levels"),
        metric_name="cloudflare_waf_total_events",
        label="Total Events",
        render_func=format_count,
    )

    # Check blocked events threshold
    yield from check_levels(
        blocked_events,
        levels_upper=extract_levels(params, "blocked_events_levels"),
        metric_name="cloudflare_waf_blocked",
        label="Blocked Events",
        render_func=format_count,
    )

    # Check challenged events threshold
    yield from check_levels(
        challenged_events,
        levels_upper=extract_levels(params, "challenged_events_levels"),
        metric_name="cloudflare_waf_challenged",
        label="Challenged Events",
        render_func=format_count,
    )

    yield Result(state=State.OK, summary=", ".join(summary_parts))


check_plugin_cloudflare_waf = CheckPlugin(
    name="cloudflare_waf",
    sections=["cloudflare"],
    service_name="Cloudflare WAF %s",
    discovery_function=discover_cloudflare_waf,
    check_function=check_cloudflare_waf,
    check_ruleset_name="cloudflare_waf",
    check_default_parameters={},
)
