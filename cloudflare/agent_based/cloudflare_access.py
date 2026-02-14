#!/usr/bin/env python3
"""Cloudflare Access check plugin."""

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
    SERVICE_ACCESS,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    extract_levels,
    get_resource_id_by_name,
    get_resource_metadata,
)


def discover_cloudflare_access(section: dict[str, Any]) -> DiscoveryResult:
    """Discover Cloudflare Access applications.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered Access application
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(
        section, SERVICE_ACCESS
    ):
        yield Service(item=resource_name)


def check_cloudflare_access(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare Access application.

    Args:
        item: Application name
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_ACCESS, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Access app not found in data")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_ACCESS, resource_id)
    metadata = get_resource_metadata(section, SERVICE_ACCESS, resource_id)

    if not metrics:
        yield Result(state=State.UNKNOWN, summary="Access app not found in data")
        return

    # Extract metric values
    policy_count = int(metrics.get("policy_count", {}).get("value", 0))
    allowed_idps = int(metrics.get("allowed_idps_count", {}).get("value", 0))

    # Get app info from metadata - item is already the name
    domain = metadata.get("domain", "")

    # Build summary - item is already the human-readable name in service name
    summary_parts = []
    if domain:
        summary_parts.append(f"Domain: {domain}")
    summary_parts.append(f"Policies: {policy_count}")
    summary_parts.append(f"IDPs: {allowed_idps}")

    # Check policy_count against thresholds
    policy_levels = extract_levels(params, "policy_count_levels")
    yield from check_levels(
        policy_count,
        levels_upper=policy_levels,
        metric_name="cloudflare_access_policies",
        label="Policies",
        render_func=str,
    )

    # Warn if no policies configured
    state = State.OK
    if policy_count == 0:
        state = State.WARN

    yield Result(state=state, summary=", ".join(summary_parts))

    # Yield remaining metrics
    yield Metric("cloudflare_access_idps", allowed_idps)


check_plugin_cloudflare_access = CheckPlugin(
    name="cloudflare_access",
    sections=["cloudflare"],
    service_name="Cloudflare Access %s",
    discovery_function=discover_cloudflare_access,
    check_function=check_cloudflare_access,
    check_ruleset_name="cloudflare_access",
    check_default_parameters={},
)
