#!/usr/bin/env python3
"""Cloudflare Load Balancer check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import simple_levels_integer, simple_levels_lower_percent


def _parameter_form_cloudflare_load_balancer() -> Dictionary:
    """Build the parameter form for load balancer checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Load Balancer Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare Load Balancer monitoring."),
        elements={
            "healthy_origin_ratio_levels": simple_levels_lower_percent(
                title="Healthy Origin Ratio (Minimum)",
                help_text="Alert when healthy origin ratio falls below these thresholds.",
                default_warn=50.0,
                default_crit=25.0,
            ),
            "origin_count_levels": simple_levels_integer(
                title="Origin Count",
                help_text="Alert when origin count changes unexpectedly.",
            ),
        },
    )


rule_spec_cloudflare_load_balancer = CheckParameters(
    name="cloudflare_load_balancer",
    title=Title("Cloudflare Load Balancer"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_load_balancer,
    condition=HostAndItemCondition(item_title=Title("Load Balancer Pool")),
)
