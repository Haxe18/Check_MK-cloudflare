#!/usr/bin/env python3
"""Cloudflare Rulesets check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import simple_levels_integer


def _parameter_form_cloudflare_rulesets() -> Dictionary:
    """Build the parameter form for Cloudflare Rulesets checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Rulesets Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare Rulesets monitoring."),
        elements={
            "ruleset_count_levels": simple_levels_integer(
                title="Total Ruleset Count",
                help_text="Alert when total ruleset count exceeds these thresholds.",
            ),
            "redirect_rules_levels": simple_levels_integer(
                title="Redirect Rules Count",
                help_text="Alert when redirect rule count exceeds these thresholds.",
            ),
            "cache_rules_levels": simple_levels_integer(
                title="Cache Rules Count",
                help_text="Alert when cache rule count exceeds these thresholds.",
            ),
            "config_rules_levels": simple_levels_integer(
                title="Config Rules Count",
                help_text="Alert when configuration rule count exceeds these thresholds.",
            ),
            "origin_rules_levels": simple_levels_integer(
                title="Origin Rules Count",
                help_text="Alert when origin rule count exceeds these thresholds.",
            ),
        },
    )


rule_spec_cloudflare_rulesets = CheckParameters(
    name="cloudflare_rulesets",
    title=Title("Cloudflare Rulesets"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_rulesets,
    condition=HostAndItemCondition(item_title=Title("Zone")),
)
