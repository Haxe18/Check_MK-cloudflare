#!/usr/bin/env python3
"""Cloudflare Tunnel check plugin."""

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
    SERVICE_TUNNEL,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    get_resource_id_by_name,
    get_resource_metadata,
)


def discover_cloudflare_tunnel(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Tunnels.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered tunnel
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_TUNNEL
    ):
        yield Service(item=resource_name)


def check_cloudflare_tunnel(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare Tunnel.

    Args:
        item: Tunnel name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_TUNNEL, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Tunnel not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_TUNNEL, resource_id)
    metadata = get_resource_metadata(section, SERVICE_TUNNEL, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Tunnel not found in data")
        return

    # Extract metric values
    status_value = metrics.get("status", {}).get("value", 0)
    connection_count = int(metrics.get("connection_count", {}).get("value", 0))

    # Get tunnel info from metadata - item is already the name
    status_text = metadata.get("status", "unknown")

    # Determine state based on tunnel status
    if status_value >= 2:  # active
        state = State.OK
    elif status_value >= 1:  # inactive
        state = State.WARN
    else:  # unknown
        state = State.CRIT

    # Build summary - item is already the human-readable name in service name
    summary_parts = [
        f"Status: {status_text}",
        f"Connections: {connection_count}",
    ]

    # Check connection_count against lower thresholds
    yield from check_levels(
        connection_count,
        levels_lower=extract_levels(params, "connection_count_levels"),
        metric_name="cloudflare_tunnel_connections",
        label="Connections",
        render_func=str,
    )

    yield Result(state=state, summary=", ".join(summary_parts))

    # Yield remaining metrics
    yield Metric("cloudflare_tunnel_status", status_value)


check_plugin_cloudflare_tunnel = CheckPlugin(
    name="cloudflare_tunnel",
    sections=["cloudflare"],
    service_name="Cloudflare Tunnel %s",
    discovery_function=discover_cloudflare_tunnel,
    check_function=check_cloudflare_tunnel,
    check_ruleset_name="cloudflare_tunnel",
    check_default_parameters={},
)
