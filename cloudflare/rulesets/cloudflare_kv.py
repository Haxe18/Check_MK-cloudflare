#!/usr/bin/env python3
"""Cloudflare KV Namespaces check parameters ruleset."""

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
    simple_levels_lower_integer,
    simple_levels_percent,
)


def _parameter_form_cloudflare_kv() -> Dictionary:
    """Build the parameter form for per-namespace KV checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare KV Namespaces Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare KV Namespaces monitoring. "
            "These thresholds apply to individual KV namespaces."
        ),
        elements={
            "reads_levels": simple_levels_integer(
                title="Read Operations",
                help_text="Alert when read operation count exceeds these thresholds (per period).",
            ),
            "writes_levels": simple_levels_integer(
                title="Write Operations",
                help_text="Alert when write operation count exceeds these thresholds (per period).",
            ),
            "key_count_levels": simple_levels_integer(
                title="Key Count (Maximum)",
                help_text="Alert when the number of keys exceeds these thresholds.",
            ),
            "key_count_levels_lower": simple_levels_lower_integer(
                title="Key Count (Minimum)",
                help_text="Alert when the number of keys falls below these thresholds.",
            ),
            "storage_levels": simple_levels_datasize(
                title="Storage Used",
                help_text="Alert when storage usage exceeds these thresholds.",
            ),
        },
    )


def _parameter_form_cloudflare_kv_global() -> Dictionary:
    """Build the parameter form for account-wide KV usage checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare KV Global Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare KV account-wide usage monitoring. "
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
            "reads_usage_levels": simple_levels_percent(
                title="Reads Usage",
                help_text="Alert when reads usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
            "writes_usage_levels": simple_levels_percent(
                title="Writes Usage",
                help_text="Alert when writes usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
            "deletes_usage_levels": simple_levels_percent(
                title="Deletes Usage",
                help_text="Alert when deletes usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
            "lists_usage_levels": simple_levels_percent(
                title="Lists Usage",
                help_text="Alert when lists usage percentage exceeds these thresholds.",
                default_warn=80.0,
                default_crit=95.0,
            ),
        },
    )


rule_spec_cloudflare_kv = CheckParameters(
    name="cloudflare_kv",
    title=Title("Cloudflare KV Namespaces"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_kv,
    condition=HostAndItemCondition(item_title=Title("KV Namespace")),
)

rule_spec_cloudflare_kv_global = CheckParameters(
    name="cloudflare_kv_global",
    title=Title("Cloudflare KV Global"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_kv_global,
    condition=HostCondition(),
)
