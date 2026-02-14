#!/usr/bin/env python3
"""Cloudflare WAF check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import simple_levels_integer


def _parameter_form_cloudflare_waf() -> Dictionary:
    """Build the parameter form for WAF checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare WAF Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare WAF/Security Events monitoring."),
        elements={
            "total_events_levels": simple_levels_integer(
                title="Total Security Events",
                help_text="Alert when total security events exceed thresholds.",
                default_warn=100,
                default_crit=1000,
            ),
            "blocked_events_levels": simple_levels_integer(
                title="Blocked Events",
                help_text="Alert when blocked events exceed thresholds.",
            ),
            "challenged_events_levels": simple_levels_integer(
                title="Challenged Events",
                help_text="Alert when challenged events exceed thresholds.",
            ),
        },
    )


rule_spec_cloudflare_waf = CheckParameters(
    name="cloudflare_waf",
    title=Title("Cloudflare WAF Events"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_waf,
    condition=HostAndItemCondition(item_title=Title("Zone")),
)
