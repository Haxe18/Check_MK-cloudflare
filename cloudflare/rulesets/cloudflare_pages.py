#!/usr/bin/env python3
"""Cloudflare Pages check parameters rulesets."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import (
    simple_levels_milliseconds,
    simple_levels_percent,
    simple_levels_seconds,
)


def _parameter_form_cloudflare_pages() -> Dictionary:
    """Build the parameter form for Cloudflare Pages checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Pages Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare Pages deployment monitoring."),
        elements={
            "building_state": DictElement(
                parameter_form=SingleChoice(
                    title=Title("State when building"),
                    help_text=Help("The check state when a deployment is currently building."),
                    elements=[
                        SingleChoiceElement(name="ok", title=Title("OK")),
                        SingleChoiceElement(name="warn", title=Title("WARN")),
                    ],
                    prefill=DefaultValue("ok"),
                ),
                required=False,
            ),
            "max_deployment_age": simple_levels_seconds(
                title="Maximum Deployment Age",
                help_text=(
                    "Alert when the last production deployment is older than these "
                    "thresholds. Use this to detect stale deployments."
                ),
            ),
        },
    )


def _parameter_form_cloudflare_pages_functions() -> Dictionary:
    """Build the parameter form for Pages Functions checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Pages Functions Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare Pages Functions monitoring. "
            "These thresholds apply to projects with Functions enabled."
        ),
        elements={
            "error_rate_levels": simple_levels_percent(
                title="Error Rate",
                help_text="Alert when Pages Functions error rate exceeds these thresholds.",
                default_warn=5.0,
                default_crit=10.0,
            ),
            "cpu_time_p50_levels": simple_levels_milliseconds(
                title="CPU Time P50",
                help_text="Alert when median CPU time exceeds these thresholds.",
            ),
            "cpu_time_p99_levels": simple_levels_milliseconds(
                title="CPU Time P99",
                help_text="Alert when 99th percentile CPU time exceeds these thresholds.",
            ),
        },
    )


rule_spec_cloudflare_pages = CheckParameters(
    name="cloudflare_pages",
    title=Title("Cloudflare Pages"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_pages,
    condition=HostAndItemCondition(item_title=Title("Pages Project")),
)


rule_spec_cloudflare_pages_functions = CheckParameters(
    name="cloudflare_pages_functions",
    title=Title("Cloudflare Pages Functions"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_pages_functions,
    condition=HostAndItemCondition(item_title=Title("Pages Project")),
)
