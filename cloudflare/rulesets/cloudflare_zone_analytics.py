#!/usr/bin/env python3
"""Cloudflare Zone Analytics check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import (
    simple_levels_datasize,
    simple_levels_integer,
    simple_levels_lower_percent,
)


def _parameter_form_cloudflare_zone_analytics() -> Dictionary:
    """Build the parameter form for zone analytics checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Zone Analytics Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare Zone Analytics monitoring. "
            "Monitors HTTP traffic including requests, bandwidth, and threats."
        ),
        elements={
            "requests_levels": simple_levels_integer(
                title="Request Count",
                help_text="Alert when request count exceeds these thresholds (per period).",
            ),
            "bandwidth_levels": simple_levels_datasize(
                title="Bandwidth",
                help_text="Alert when bandwidth exceeds these thresholds (per period).",
            ),
            "threats_levels": simple_levels_integer(
                title="Threat Count",
                help_text="Alert when threat count exceeds these thresholds (per period).",
                default_warn=100,
                default_crit=1000,
            ),
            "cache_hit_ratio_levels": simple_levels_lower_percent(
                title="Cache Hit Ratio (Lower)",
                help_text="Alert when cache hit ratio falls below these thresholds.",
                default_warn=50.0,
                default_crit=30.0,
            ),
        },
    )


rule_spec_cloudflare_zone_analytics = CheckParameters(
    name="cloudflare_zone_analytics",
    title=Title("Cloudflare Zone Analytics"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_zone_analytics,
    condition=HostAndItemCondition(item_title=Title("Zone")),
)
