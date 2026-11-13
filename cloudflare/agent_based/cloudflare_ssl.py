#!/usr/bin/env python3
"""Cloudflare SSL/TLS check plugin."""

from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

from ..lib.constants import STATE_MAP
from .cloudflare_helpers import (
    SERVICE_SSL,
    discover_cloudflare_resources_by_name,
    get_resource_id_by_name,
    get_resource_metadata,
)


def discover_cloudflare_ssl(section: dict[str, Any]) -> DiscoveryResult:
    """Discover zones for SSL/TLS monitoring.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for each discovered zone
    """
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_SSL):
        yield Service(item=resource_name)


def check_cloudflare_ssl(
    item: str,
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check SSL/TLS status for a zone.

    Args:
        item: Zone name (domain)
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results (no metrics - pure status check)
    """
    # Look up resource ID by name for metadata lookup
    resource_id = get_resource_id_by_name(section, SERVICE_SSL, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="SSL data not found")
        return

    metadata = get_resource_metadata(section, SERVICE_SSL, resource_id)

    if not metadata:
        yield Result(state=State.UNKNOWN, summary="SSL data not found")
        return

    # Get SSL data from metadata - item is already the zone name
    cert_status = metadata.get("certificate_status", "unknown")
    ssl_mode = metadata.get("ssl_mode", "unknown")

    # 'certificate_status' is derived from the SSL mode (certificates are not checked):
    # active = SSL switched on, disabled = mode "off", unknown = mode could not be read
    if cert_status == "active":
        state = State.OK
    elif cert_status == "disabled":
        # SSL is disabled (mode=off) - this is a configuration choice
        state = State.WARN
    elif cert_status == "pending":
        # Check if user wants to warn on pending (default: warn)
        state = State(STATE_MAP.get(params.get("warn_on_pending", "warn"), 1))
    else:
        # SSL mode could not be read (API error, missing permission)
        state = State.UNKNOWN

    # Format SSL mode for display
    mode_display = ssl_mode.upper() if ssl_mode != "unknown" else "Unknown"
    ssl_display = {"active": "enabled", "disabled": "disabled"}.get(cert_status, cert_status)

    yield Result(
        state=state,
        summary=f"SSL {ssl_display}, Mode: {mode_display}",
    )


check_plugin_cloudflare_ssl = CheckPlugin(
    name="cloudflare_ssl",
    sections=["cloudflare"],
    service_name="Cloudflare SSL %s",
    discovery_function=discover_cloudflare_ssl,
    check_function=check_cloudflare_ssl,
    check_ruleset_name="cloudflare_ssl",
    check_default_parameters={"warn_on_pending": "warn"},
)
