#!/usr/bin/env python3
"""Cloudflare D1 Database check parameters ruleset."""

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    Topic,
)

from .cloudflare_helpers import (
    simple_levels_datasize,
    simple_levels_integer,
    simple_levels_percent,
)


def _parameter_form_cloudflare_d1() -> Dictionary:
    """Build the parameter form for per-database D1 checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare D1 Database Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare D1 Database monitoring."),
        elements={
            "storage_levels": simple_levels_datasize(
                title="Storage Levels",
                help_text="Alert when storage usage exceeds these thresholds.",
            ),
            "query_count_levels": simple_levels_integer(
                title="Query Count Levels",
                help_text="Alert when query count exceeds these thresholds.",
            ),
        },
    )


def _parameter_form_cloudflare_d1_global() -> Dictionary:
    """Build the parameter form for account-wide D1 usage checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare D1 Global Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare D1 account-wide usage monitoring. "
            "Paid plans are usage-based; free plans use included daily thresholds."
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
            "storage_usage_levels": simple_levels_percent(
                title="Storage Usage",
                help_text="Alert when storage usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
            "rows_read_usage_levels": simple_levels_percent(
                title="Rows Read Usage",
                help_text="Alert when daily rows read usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
            "rows_written_usage_levels": simple_levels_percent(
                title="Rows Written Usage",
                help_text=(
                    "Alert when daily rows written usage percentage exceeds these thresholds."
                ),
                default_warn=80.0,
                default_crit=95.0,
            ),
        },
    )


rule_spec_cloudflare_d1 = CheckParameters(
    name="cloudflare_d1",
    title=Title("Cloudflare D1 Database"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_d1,
    condition=HostAndItemCondition(item_title=Title("D1 Database")),
)

rule_spec_cloudflare_d1_global = CheckParameters(
    name="cloudflare_d1_global",
    title=Title("Cloudflare D1 Global"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_d1_global,
    condition=HostCondition(),
)
