#!/usr/bin/env python3
"""Cloudflare R2 Buckets check parameters ruleset."""

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


def _parameter_form_cloudflare_r2() -> Dictionary:
    """Build the parameter form for per-bucket R2 checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare R2 Buckets Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare R2 Buckets monitoring."),
        elements={
            "storage_levels": simple_levels_datasize(
                title="Storage Used",
                help_text="Alert when storage usage exceeds these thresholds.",
            ),
            "object_count_levels": simple_levels_integer(
                title="Object Count",
                help_text="Alert when object count exceeds these thresholds.",
            ),
        },
    )


def _parameter_form_cloudflare_r2_global() -> Dictionary:
    """Build the parameter form for account-wide R2 usage checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare R2 Global Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare R2 account-wide usage monitoring. "
            "Storage is shown against the included free tier (10 GiB). "
            "R2 remains usage-based beyond this tier."
        ),
        elements={
            "free_tier_monitoring": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Free tier monitoring"),
                    label=Label("Alert based on free tier levels"),
                    help_text=Help(
                        "Enable monitoring against included free tier usage (10 GiB). "
                        "This affects free-tier usage percentage checks only."
                    ),
                    prefill=DefaultValue(True),
                ),
                required=True,
            ),
            "storage_usage_levels": simple_levels_percent(
                title="Storage Usage",
                help_text=(
                    "Alert when storage usage percentage exceeds these thresholds "
                    "(of included free tier)."
                ),
                default_warn=80.0,
                default_crit=95.0,
            ),
        },
    )


rule_spec_cloudflare_r2 = CheckParameters(
    name="cloudflare_r2",
    title=Title("Cloudflare R2 Buckets"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_r2,
    condition=HostAndItemCondition(item_title=Title("R2 Bucket")),
)

rule_spec_cloudflare_r2_global = CheckParameters(
    name="cloudflare_r2_global",
    title=Title("Cloudflare R2 Global"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_r2_global,
    condition=HostCondition(),
)
