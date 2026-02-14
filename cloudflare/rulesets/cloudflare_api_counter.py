#!/usr/bin/env python3
"""Cloudflare API Counter check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, List, String
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_cloudflare_api_counter() -> Dictionary:
    """Build the parameter form for Cloudflare API usage checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare API Usage Settings"),
        help_text=Help("Configure settings for Cloudflare API Usage monitoring."),
        elements={
            "ignore_error_patterns": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("Ignore errors containing (substring match, no regex)"),
                    help_text=Help(
                        "List of substrings (no regex). Errors containing any of these "
                        "substrings will be ignored and not trigger WARN state. "
                        "Example: 'does not have permission'"
                    ),
                ),
                required=False,
            ),
        },
    )


rule_spec_cloudflare_api_counter = CheckParameters(
    name="cloudflare_api_counter",
    title=Title("Cloudflare API Usage"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_api_counter,
    condition=HostCondition(),
)
