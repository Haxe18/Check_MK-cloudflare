#!/usr/bin/env python3
"""Cloudflare DNS Analytics check plugin."""

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
    SERVICE_DNS_ANALYTICS,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_count,
    get_resource_id_by_name,
)


def discover_cloudflare_dns_analytics(section: dict[str, Any]) -> DiscoveryResult:
    """Discover zones for DNS Analytics.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered zone
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_DNS_ANALYTICS
    ):
        yield Service(item=resource_name)


def check_cloudflare_dns_analytics(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check DNS Analytics.

    Args:
        item: Zone name (domain)
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_DNS_ANALYTICS, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="DNS analytics not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_DNS_ANALYTICS, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="DNS analytics not found in data")
        return

    # Extract metric values
    query_count = metrics.get("query_count", {}).get("value", 0)
    noerror_count = metrics.get("noerror_count", {}).get("value", 0)
    nxdomain_count = metrics.get("nxdomain_count", {}).get("value", 0)
    servfail_count = metrics.get("servfail_count", {}).get("value", 0)

    # Build summary - item is already the domain name in service name
    summary_parts = [
        f"Queries: {format_count(query_count)}",
    ]

    if noerror_count > 0:
        summary_parts.append(f"OK: {format_count(noerror_count)}")
    if nxdomain_count > 0:
        summary_parts.append(f"NXDOMAIN: {format_count(nxdomain_count)}")
    if servfail_count > 0:
        summary_parts.append(f"SERVFAIL: {format_count(servfail_count)}")

    # Check thresholds
    yield from check_levels(
        query_count,
        levels_upper=extract_levels(params, "query_count_levels"),
        metric_name="cloudflare_dns_query_count",
        label="Queries",
        render_func=format_count,
    )

    yield from check_levels(
        nxdomain_count,
        levels_upper=extract_levels(params, "nxdomain_levels"),
        metric_name="cloudflare_dns_nxdomain",
        label="NXDOMAIN",
        render_func=format_count,
    )

    yield from check_levels(
        servfail_count,
        levels_upper=extract_levels(params, "servfail_levels"),
        metric_name="cloudflare_dns_servfail",
        label="SERVFAIL",
        render_func=format_count,
    )

    yield Result(state=State.OK, summary=", ".join(summary_parts))

    # Yield remaining metrics (noerror has no threshold)
    yield Metric("cloudflare_dns_noerror", noerror_count)


check_plugin_cloudflare_dns_analytics = CheckPlugin(
    name="cloudflare_dns_analytics",
    sections=["cloudflare"],
    service_name="Cloudflare DNS Analytics %s",
    discovery_function=discover_cloudflare_dns_analytics,
    check_function=check_cloudflare_dns_analytics,
    check_ruleset_name="cloudflare_dns_analytics",
    check_default_parameters={},
)
