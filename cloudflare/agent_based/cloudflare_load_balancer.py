#!/usr/bin/env python3
"""Cloudflare Load Balancer check plugin."""

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
    SERVICE_LOAD_BALANCER,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    get_resource_id_by_name,
)


def discover_cloudflare_load_balancer(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Load Balancer pools.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered pool
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_LOAD_BALANCER
    ):
        yield Service(item=resource_name)


def check_cloudflare_load_balancer(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Load Balancer pool.

    Args:
        item: Pool name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_LOAD_BALANCER, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Load balancer pool not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_LOAD_BALANCER, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Load balancer pool not found in data")
        return

    # Extract metric values
    healthy = metrics.get("healthy", {}).get("value", 0) > 0
    origin_count = int(metrics.get("origin_count", {}).get("value", 0))
    healthy_origin_count = int(metrics.get("healthy_origin_count", {}).get("value", 0))
    health_rtt_avg = metrics.get("health_rtt_avg", {}).get("value", 0)

    # Calculate healthy ratio
    healthy_ratio = (healthy_origin_count / origin_count * 100) if origin_count > 0 else 0

    # Determine state
    if not healthy:
        state = State.CRIT
    elif healthy_origin_count < origin_count:
        state = State.WARN
    else:
        state = State.OK

    # Build summary - item is already the human-readable name in service name
    summary_parts = [
        f"Pool: {'Healthy' if healthy else 'UNHEALTHY'}",
        f"Origins: {healthy_origin_count}/{origin_count} healthy ({healthy_ratio:.0f}%)",
    ]

    if health_rtt_avg > 0:
        summary_parts.append(f"RTT: {health_rtt_avg:.0f}ms")

    # Check thresholds - healthy_ratio is LOWER threshold
    yield from check_levels(
        healthy_ratio,
        levels_lower=extract_levels(params, "healthy_origin_ratio_levels"),
        metric_name="cloudflare_lb_healthy_ratio",
        label="Healthy Ratio",
        render_func=lambda x: f"{x:.0f}%",
    )

    yield from check_levels(
        origin_count,
        levels_upper=extract_levels(params, "origin_count_levels"),
        metric_name="cloudflare_lb_origin_count",
        label="Origin Count",
        render_func=str,
    )

    yield Result(state=state, summary=", ".join(summary_parts))

    # Yield remaining metrics
    yield Metric("cloudflare_lb_healthy", 1.0 if healthy else 0.0)
    yield Metric("cloudflare_lb_healthy_origins", healthy_origin_count)

    # Health check RTT (always output for continuous graphs)
    yield Metric("cloudflare_lb_rtt", health_rtt_avg)


check_plugin_cloudflare_load_balancer = CheckPlugin(
    name="cloudflare_load_balancer",
    sections=["cloudflare"],
    service_name="Cloudflare LB Pool %s",
    discovery_function=discover_cloudflare_load_balancer,
    check_function=check_cloudflare_load_balancer,
    check_ruleset_name="cloudflare_load_balancer",
    check_default_parameters={"healthy_origin_ratio_levels": (50.0, 25.0)},
)
