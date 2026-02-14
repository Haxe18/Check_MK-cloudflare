#!/usr/bin/env python3
"""Cloudflare Tunnel check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import simple_levels_lower_integer


def _parameter_form_cloudflare_tunnel() -> Dictionary:
    """Build the parameter form for tunnel checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Tunnel Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare Tunnel monitoring."),
        elements={
            "connection_count_levels": simple_levels_lower_integer(
                title="Connection Count (Minimum)",
                help_text="Alert when connection count falls below these thresholds.",
            ),
        },
    )


rule_spec_cloudflare_tunnel = CheckParameters(
    name="cloudflare_tunnel",
    title=Title("Cloudflare Tunnel"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_tunnel,
    condition=HostAndItemCondition(item_title=Title("Tunnel")),
)
