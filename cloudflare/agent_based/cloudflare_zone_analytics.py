#!/usr/bin/env python3
"""Cloudflare Zone Analytics check plugin."""

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
    SERVICE_ZONE_ANALYTICS,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    format_bytes,
    format_count,
    get_resource_id_by_name,
)


def discover_cloudflare_zone_analytics(section: dict[str, Any]) -> DiscoveryResult:
    """Discover zones for Zone Analytics.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered zone
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_ZONE_ANALYTICS
    ):
        yield Service(item=resource_name)


def check_cloudflare_zone_analytics(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Zone Analytics.

    Args:
        item: Zone name (domain)
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_ZONE_ANALYTICS, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Zone analytics not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_ZONE_ANALYTICS, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Zone analytics not found in data")
        return

    # Extract metric values
    requests = metrics.get("requests", {}).get("value", 0)
    bandwidth = metrics.get("bandwidth", {}).get("value", 0)
    threats = metrics.get("threats", {}).get("value", 0)
    page_views = metrics.get("page_views", {}).get("value", 0)
    cached_requests = metrics.get("cached_requests", {}).get("value", 0)
    cache_hit_ratio = metrics.get("cache_hit_ratio", {}).get("value", 0)

    # Performance metrics (Pro+ plans)
    ttfb_p50 = metrics.get("ttfb_p50", {}).get("value", 0)
    ttfb_p95 = metrics.get("ttfb_p95", {}).get("value", 0)
    ttfb_p99 = metrics.get("ttfb_p99", {}).get("value", 0)
    origin_response_p50 = metrics.get("origin_response_p50", {}).get("value", 0)
    origin_response_p95 = metrics.get("origin_response_p95", {}).get("value", 0)
    origin_response_p99 = metrics.get("origin_response_p99", {}).get("value", 0)
    edge_dns_p50 = metrics.get("edge_dns_p50", {}).get("value", 0)
    edge_dns_p95 = metrics.get("edge_dns_p95", {}).get("value", 0)
    edge_dns_p99 = metrics.get("edge_dns_p99", {}).get("value", 0)

    # Build summary - item is already the domain name in service name
    summary_parts = [
        f"Requests: {format_count(requests)}",
        f"Bandwidth: {format_bytes(bandwidth)}",
        f"Cache: {cache_hit_ratio:.1f}%",
    ]

    if ttfb_p50 > 0:
        summary_parts.append(f"TTFB P50: {ttfb_p50:.0f}ms")

    if threats > 0:
        summary_parts.append(f"Threats: {format_count(threats)}")

    # Check thresholds
    yield from check_levels(
        requests,
        levels_upper=extract_levels(params, "requests_levels"),
        metric_name="cloudflare_zone_requests",
        label="Requests",
        render_func=format_count,
    )

    yield from check_levels(
        bandwidth,
        levels_upper=extract_levels(params, "bandwidth_levels"),
        metric_name="cloudflare_zone_bandwidth",
        label="Bandwidth",
        render_func=format_bytes,
    )

    yield from check_levels(
        threats,
        levels_upper=extract_levels(params, "threats_levels"),
        metric_name="cloudflare_zone_threats",
        label="Threats",
        render_func=format_count,
    )

    yield from check_levels(
        cache_hit_ratio,
        levels_lower=extract_levels(params, "cache_hit_ratio_levels"),
        metric_name="cloudflare_zone_cache_hit_ratio",
        label="Cache Hit Ratio",
        render_func=lambda x: f"{x:.1f}%",
    )

    yield Result(state=State.OK, summary=", ".join(summary_parts))

    # Yield remaining metrics (those not covered by check_levels above)
    yield Metric("cloudflare_zone_page_views", page_views)
    yield Metric("cloudflare_zone_cached_requests", cached_requests)

    # Performance metrics (Pro+ plans) - TTFB (always output for continuous graphs)
    yield Metric("cloudflare_zone_ttfb_p50", ttfb_p50)
    yield Metric("cloudflare_zone_ttfb_p95", ttfb_p95)
    yield Metric("cloudflare_zone_ttfb_p99", ttfb_p99)

    # Origin Response Duration
    yield Metric("cloudflare_zone_origin_p50", origin_response_p50)
    yield Metric("cloudflare_zone_origin_p95", origin_response_p95)
    yield Metric("cloudflare_zone_origin_p99", origin_response_p99)

    # Edge DNS Response Time
    yield Metric("cloudflare_zone_edge_dns_p50", edge_dns_p50)
    yield Metric("cloudflare_zone_edge_dns_p95", edge_dns_p95)
    yield Metric("cloudflare_zone_edge_dns_p99", edge_dns_p99)


check_plugin_cloudflare_zone_analytics = CheckPlugin(
    name="cloudflare_zone_analytics",
    sections=["cloudflare"],
    service_name="Cloudflare Zone Analytics %s",
    discovery_function=discover_cloudflare_zone_analytics,
    check_function=check_cloudflare_zone_analytics,
    check_ruleset_name="cloudflare_zone_analytics",
    check_default_parameters={},
)
