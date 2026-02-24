#!/usr/bin/env python3
"""Main Cloudflare agent section parser and API counter check."""

import json
from collections import defaultdict
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
)


def parse_cloudflare(string_table: list[list[str]]) -> dict[str, Any]:
    """Parse the Cloudflare agent output.

    Args:
        string_table: Raw agent output

    Returns:
        Parsed section data with CloudflareMetrics, CloudflareAPICounter, CloudflareConfig
    """
    try:
        raw_json = "".join("".join(line) for line in string_table)
        if not raw_json.strip():
            return {
                "CloudflareMetrics": {},
                "CloudflareAPICounter": {},
                "CloudflareConfig": {},
            }

        parsed = json.loads(raw_json)
        if not isinstance(parsed, dict):
            return {
                "CloudflareMetrics": {},
                "CloudflareAPICounter": {
                    "error": f"Unexpected JSON payload type: {type(parsed).__name__}"
                },
                "CloudflareConfig": {},
                "CloudflareErrors": [],
                "CloudflareSkippedProFeatures": {},
                "CloudflareUnusedPermissions": {},
            }
        return {
            "CloudflareMetrics": parsed.get("CloudflareMetrics", {}),
            "CloudflareAPICounter": parsed.get("CloudflareAPICounter", {}),
            "CloudflareConfig": parsed.get("CloudflareConfig", {}),
            "CloudflareErrors": parsed.get("CloudflareErrors", []),
            "CloudflareSkippedProFeatures": parsed.get("CloudflareSkippedProFeatures", {}),
            "CloudflareUnusedPermissions": parsed.get("CloudflareUnusedPermissions", {}),
        }
    except json.JSONDecodeError:
        return {
            "CloudflareMetrics": {},
            "CloudflareAPICounter": {"error": "JSON decode error"},
            "CloudflareConfig": {},
        }


agent_section_cloudflare = AgentSection(
    name="cloudflare",
    parse_function=parse_cloudflare,
)


# =============================================================================
# API Counter Check
# =============================================================================


def discover_cloudflare_api_counter(section: dict[str, Any]) -> DiscoveryResult:
    """Discover the Cloudflare API counter service.

    Args:
        section: Parsed cloudflare section

    Yields:
        Service for API counter if data is available
    """
    api_counter = section.get("CloudflareAPICounter", {})
    if not isinstance(api_counter, dict):
        return
    if "requests_made" in api_counter or "error" in api_counter:
        yield Service()


def check_cloudflare_api_counter(
    params: dict[str, Any],
    section: dict[str, Any],
) -> CheckResult:
    """Check Cloudflare API usage.

    Args:
        params: Check parameters
        section: Parsed cloudflare section

    Yields:
        Check results and metrics
    """
    api_counter = section.get("CloudflareAPICounter", {})
    config = section.get("CloudflareConfig", {})
    errors = section.get("CloudflareErrors", [])
    skipped_pro_features = section.get("CloudflareSkippedProFeatures", {})
    unused_permissions = section.get("CloudflareUnusedPermissions", {})

    if "error" in api_counter:
        yield Result(
            state=State.CRIT,
            summary=f"Agent error: {api_counter['error']}",
        )
        # Keep the API error graph continuous: the agent error counts as one error
        yield Metric("cloudflare_api_errors", 1)
        return

    requests_made = api_counter.get("requests_made", 0)
    elapsed_seconds = api_counter.get("elapsed_seconds", 0)
    requests_by_type = api_counter.get("requests_by_type", {})

    services_count = config.get("services_count", 0)
    cache_ttl = config.get("cache_ttl", 300)

    # Build summary
    summary_parts = [
        f"API calls: {requests_made}",
        f"Services: {services_count}",
    ]

    # Filter errors based on ignore patterns (match on message field)
    ignore_patterns_param = params.get("ignore_error_patterns", [])
    ignore_patterns = [
        pattern for pattern in ignore_patterns_param if isinstance(pattern, str) and pattern
    ]
    active_errors: list[dict[str, Any]] = []
    ignored_errors: list[dict[str, Any]] = []

    for error in errors:
        if not isinstance(error, dict):
            continue

        error_msg = error.get("message", "")

        if any(pattern in error_msg for pattern in ignore_patterns):
            ignored_errors.append(error)
        else:
            active_errors.append(error)

    # Set state based on active (non-ignored) errors only
    state = State.OK
    if active_errors:
        state = State.WARN
        # Build category summary (e.g., "2 api, 1 discovery")
        by_category: dict[str, int] = defaultdict(int)
        for err in active_errors:
            by_category[err.get("category", "unknown")] += 1
        error_summary = ", ".join(f"{c} {cat}" for cat, c in sorted(by_category.items()))
        summary_parts.append(f"Errors: {error_summary}")

    if ignored_errors:
        summary_parts.append(f"Ignored: {len(ignored_errors)}")

    # Build details with skipped Pro+ features info
    details_lines = [
        f"Requests made: {requests_made}",
        f"Requests by type: {requests_by_type}",
        f"Elapsed time: {elapsed_seconds:.1f}s",
        f"Cache TTL: {cache_ttl}s",
        f"Services monitored: {', '.join(config.get('services', []))}",
    ]

    # Add skipped Pro+ features info (e.g., WAF for Free zones)
    if skipped_pro_features:
        details_lines.append("Pro+ features skipped for Free zones:")
        for service, zones in skipped_pro_features.items():
            details_lines.append(f"  - {service}: {', '.join(zones)}")

    # Add unused permissions info (services with no resources)
    if unused_permissions:
        details_lines.append("Unused permissions (no resources found):")
        for service, permission in unused_permissions.items():
            details_lines.append(f"  - {service}: {permission}")

    if active_errors:
        details_lines.append("Active errors:")
        for err in active_errors:
            cat = err.get("category", "unknown")
            svc = err.get("service", "unknown")
            msg = err.get("message", str(err))
            details_lines.append(f"  - [{cat}/{svc}] {msg}")

    if ignored_errors:
        details_lines.append("Ignored errors:")
        for err in ignored_errors:
            cat = err.get("category", "unknown")
            svc = err.get("service", "unknown")
            msg = err.get("message", str(err))
            details_lines.append(f"  - [{cat}/{svc}] {msg}")

    yield Result(
        state=state,
        summary=", ".join(summary_parts),
        details="\n".join(details_lines),
    )

    # Yield metrics
    yield Metric("cloudflare_api_requests", requests_made)
    yield Metric("cloudflare_api_errors", len(active_errors))
    yield Metric("cloudflare_api_elapsed_time", elapsed_seconds)

    # Per-type metrics
    for req_type, count in requests_by_type.items():
        yield Metric(f"cloudflare_api_requests_{req_type}", count)


check_plugin_cloudflare_api_counter = CheckPlugin(
    name="cloudflare_api_counter",
    sections=["cloudflare"],
    service_name="Cloudflare API Usage",
    discovery_function=discover_cloudflare_api_counter,
    check_function=check_cloudflare_api_counter,
    check_ruleset_name="cloudflare_api_counter",
    check_default_parameters={},
)
