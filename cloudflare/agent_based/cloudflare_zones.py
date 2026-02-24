#!/usr/bin/env python3
"""Cloudflare DNS Zones check plugin."""

from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

from .cloudflare_helpers import (
    SERVICE_ZONES,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    get_resource_id_by_name,
    get_resource_metadata,
)

# Mapping from SingleChoice string values to Check_MK State enum integers
STATE_MAP = {"ok": 0, "warn": 1, "crit": 2}


def discover_cloudflare_zones(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare DNS Zones.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered zone
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_ZONES
    ):
        yield Service(item=resource_name)


def check_cloudflare_zones(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check a Cloudflare DNS Zone.

    Args:
        item: Zone name (domain)
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_ZONES, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Zone not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_ZONES, resource_id)
    metadata = get_resource_metadata(section, SERVICE_ZONES, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Zone not found in data")
        return

    # Get zone info from metadata - item is already the zone name
    status = metadata.get("status", "unknown")
    paused = metadata.get("paused", False)
    plan = metadata.get("plan", "")

    # Determine state
    if paused:
        state = State(STATE_MAP.get(params.get("state_paused", "warn"), 1))
        summary = "PAUSED"
    elif status == "active":
        state = State.OK
        summary = status
    else:
        state = State(STATE_MAP.get(params.get("state_not_active", "warn"), 1))
        summary = status

    if plan:
        summary += f" (Plan: {plan})"

    yield Result(state=state, summary=summary)


check_plugin_cloudflare_zones = CheckPlugin(
    name="cloudflare_zones",
    sections=["cloudflare"],
    service_name="Cloudflare Zone %s",
    discovery_function=discover_cloudflare_zones,
    check_function=check_cloudflare_zones,
    check_ruleset_name="cloudflare_zones",
    check_default_parameters={},
)
