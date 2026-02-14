#!/usr/bin/env python3
"""Cloudflare Rulesets check plugin."""

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
    SERVICE_RULESETS,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    get_resource_id_by_name,
)


def discover_cloudflare_rulesets(section: dict[str, Any]) -> DiscoveryResult:
    """Discover zones for Rulesets monitoring.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered zone
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_RULESETS
    ):
        yield Service(item=resource_name)


def check_cloudflare_rulesets(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Rulesets.

    Args:
        item: Zone name (domain)
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_RULESETS, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Rulesets data not found")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_RULESETS, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Rulesets data not found")
        return

    # Extract metric values
    ruleset_count = int(metrics.get("ruleset_count", {}).get("value", 0))
    redirect_rules = int(metrics.get("redirect_rules", {}).get("value", 0))
    cache_rules = int(metrics.get("cache_rules", {}).get("value", 0))
    config_rules = int(metrics.get("config_rules", {}).get("value", 0))
    origin_rules = int(metrics.get("origin_rules", {}).get("value", 0))

    # Build summary - item is already the domain name in service name
    summary = f"{ruleset_count} rulesets"
    details_parts = []
    if redirect_rules > 0:
        details_parts.append(f"Redirect: {redirect_rules}")
    if cache_rules > 0:
        details_parts.append(f"Cache: {cache_rules}")
    if config_rules > 0:
        details_parts.append(f"Config: {config_rules}")
    if origin_rules > 0:
        details_parts.append(f"Origin: {origin_rules}")

    if details_parts:
        summary += f" ({', '.join(details_parts)})"

    # Check thresholds
    yield from check_levels(
        ruleset_count,
        levels_upper=extract_levels(params, "ruleset_count_levels"),
        metric_name="cloudflare_rulesets_total",
        label="Total Rulesets",
        render_func=str,
    )

    yield from check_levels(
        redirect_rules,
        levels_upper=extract_levels(params, "redirect_rules_levels"),
        metric_name="cloudflare_rulesets_redirect",
        label="Redirect Rules",
        render_func=str,
    )

    yield from check_levels(
        cache_rules,
        levels_upper=extract_levels(params, "cache_rules_levels"),
        metric_name="cloudflare_rulesets_cache",
        label="Cache Rules",
        render_func=str,
    )

    yield from check_levels(
        config_rules,
        levels_upper=extract_levels(params, "config_rules_levels"),
        metric_name="cloudflare_rulesets_config",
        label="Config Rules",
        render_func=str,
    )

    yield from check_levels(
        origin_rules,
        levels_upper=extract_levels(params, "origin_rules_levels"),
        metric_name="cloudflare_rulesets_origin",
        label="Origin Rules",
        render_func=str,
    )

    yield Result(state=State.OK, summary=summary)


check_plugin_cloudflare_rulesets = CheckPlugin(
    name="cloudflare_rulesets",
    sections=["cloudflare"],
    service_name="Cloudflare Rulesets %s",
    discovery_function=discover_cloudflare_rulesets,
    check_function=check_cloudflare_rulesets,
    check_ruleset_name="cloudflare_rulesets",
    check_default_parameters={},
)
