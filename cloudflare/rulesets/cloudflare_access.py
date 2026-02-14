#!/usr/bin/env python3
"""Cloudflare Access check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import simple_levels_integer


def _parameter_form_cloudflare_access() -> Dictionary:
    """Build the parameter form for Cloudflare Access checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Access Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare Access monitoring."),
        elements={
            "policy_count_levels": simple_levels_integer(
                title="Policy Count",
                help_text="Alert when policy count exceeds these thresholds.",
            ),
        },
    )


rule_spec_cloudflare_access = CheckParameters(
    name="cloudflare_access",
    title=Title("Cloudflare Access"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_access,
    condition=HostAndItemCondition(item_title=Title("Access Application")),
)
