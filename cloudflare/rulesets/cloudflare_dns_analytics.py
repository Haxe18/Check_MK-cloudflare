#!/usr/bin/env python3
"""Cloudflare DNS Analytics check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

from .cloudflare_helpers import (
    simple_levels_integer,
)


def _parameter_form_cloudflare_dns_analytics() -> Dictionary:
    """Build the parameter form for DNS analytics checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare DNS Analytics Thresholds"),
        help_text=Help(
            "Configure thresholds for Cloudflare DNS Analytics monitoring. "
            "Monitors DNS queries and response times."
        ),
        elements={
            "query_count_levels": simple_levels_integer(
                title="Query Count",
                help_text="Alert when DNS query count exceeds these thresholds (per period).",
            ),
            "nxdomain_levels": simple_levels_integer(
                title="NXDOMAIN Count",
                help_text="Alert when NXDOMAIN response count exceeds these thresholds.",
            ),
            "servfail_levels": simple_levels_integer(
                title="SERVFAIL Count",
                help_text="Alert when SERVFAIL response count exceeds these thresholds.",
            ),
        },
    )


rule_spec_cloudflare_dns_analytics = CheckParameters(
    name="cloudflare_dns_analytics",
    title=Title("Cloudflare DNS Analytics"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_dns_analytics,
    condition=HostAndItemCondition(item_title=Title("Zone")),
)
