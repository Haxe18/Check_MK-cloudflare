#!/usr/bin/env python3
"""Cloudflare Workers check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import (
    simple_levels_integer,
    simple_levels_milliseconds,
    simple_levels_percent,
)


def _parameter_form_cloudflare_workers() -> Dictionary:
    """Build the parameter form for per-worker checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Workers Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare Workers monitoring. "
            "These thresholds apply to individual worker scripts."
        ),
        elements={
            "error_rate_levels": simple_levels_percent(
                title="Error Rate",
                help_text="Alert when worker error rate exceeds these thresholds.",
                default_warn=5.0,
                default_crit=10.0,
            ),
            "cpu_time_p50_levels": simple_levels_milliseconds(
                title="CPU Time P50",
                help_text="Alert when median CPU time exceeds these thresholds.",
            ),
            "cpu_time_p90_levels": simple_levels_milliseconds(
                title="CPU Time P90",
                help_text="Alert when 90th percentile CPU time exceeds these thresholds.",
            ),
            "cpu_time_p99_levels": simple_levels_milliseconds(
                title="CPU Time P99",
                help_text="Alert when 99th percentile CPU time exceeds these thresholds.",
            ),
            "cpu_time_p999_levels": simple_levels_milliseconds(
                title="CPU Time P999",
                help_text="Alert when 99.9th percentile CPU time exceeds these thresholds.",
            ),
            "wall_time_p50_levels": simple_levels_milliseconds(
                title="Wall Time P50",
                help_text="Alert when median Wall time exceeds these thresholds.",
            ),
            "wall_time_p90_levels": simple_levels_milliseconds(
                title="Wall Time P90",
                help_text="Alert when 90th percentile Wall time exceeds these thresholds.",
            ),
            "wall_time_p99_levels": simple_levels_milliseconds(
                title="Wall Time P99",
                help_text="Alert when 99th percentile Wall time exceeds these thresholds.",
            ),
            "wall_time_p999_levels": simple_levels_milliseconds(
                title="Wall Time P999",
                help_text="Alert when 99.9th percentile Wall time exceeds these thresholds.",
            ),
            "duration_p50_levels": simple_levels_milliseconds(
                title="Request Duration P50",
                help_text="Alert when median Request Duration exceeds these thresholds.",
            ),
            "duration_p90_levels": simple_levels_milliseconds(
                title="Request Duration P90",
                help_text="Alert when 90th percentile Request Duration exceeds these thresholds.",
            ),
            "duration_p99_levels": simple_levels_milliseconds(
                title="Request Duration P99",
                help_text="Alert when 99th percentile Request Duration exceeds these thresholds.",
            ),
            "duration_p999_levels": simple_levels_milliseconds(
                title="Request Duration P999",
                help_text="Alert when 99.9th percentile Request Duration exceeds these thresholds.",
            ),
            "requests_levels": simple_levels_integer(
                title="Request Count",
                help_text="Alert when request count exceeds these thresholds (per period).",
            ),
            "errors_levels": simple_levels_integer(
                title="Error Count",
                help_text="Alert when error count exceeds these thresholds (per period).",
            ),
        },
    )


rule_spec_cloudflare_workers = CheckParameters(
    name="cloudflare_workers",
    title=Title("Cloudflare Workers"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_workers,
    condition=HostAndItemCondition(item_title=Title("Worker Script")),
)
