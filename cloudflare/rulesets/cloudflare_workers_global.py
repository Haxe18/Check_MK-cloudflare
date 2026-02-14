#!/usr/bin/env python3
"""Cloudflare Workers Global check parameters ruleset."""

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

from .cloudflare_helpers import simple_levels_percent


def _parameter_form_cloudflare_workers_global() -> Dictionary:
    """Build the parameter form for account-wide Workers usage checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Workers Global Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare Workers Global monitoring. "
            "Workers usage is free-tier based and usage-based on paid plans."
        ),
        elements={
            "free_tier_monitoring": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Free tier monitoring"),
                    label=Label("Alert based on free tier levels"),
                    help_text=Help(
                        "Enable monitoring against free-tier included usage. "
                        "This affects free-tier usage percentage checks only."
                    ),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "daily_usage_levels": simple_levels_percent(
                title="Daily Usage",
                help_text="Alert when daily usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
        },
    )


rule_spec_cloudflare_workers_global = CheckParameters(
    name="cloudflare_workers_global",
    title=Title("Cloudflare Workers Global"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_workers_global,
    condition=HostCondition(),
)
