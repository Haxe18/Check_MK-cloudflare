#!/usr/bin/env python3
"""Cloudflare SSL/TLS check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_cloudflare_ssl() -> Dictionary:
    """Build the parameter form for SSL/TLS checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare SSL/TLS Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare SSL/TLS monitoring."),
        elements={
            "warn_on_pending": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Certificate Pending Status"),
                    help_text=Help(
                        "Configure the behavior when a certificate is in pending status "
                        "(pending_validation, pending_issuance, or pending_deployment)."
                    ),
                    elements=[
                        SingleChoiceElement(name="warn", title=Title("Warn on pending")),
                        SingleChoiceElement(name="ok", title=Title("OK on pending")),
                    ],
                    prefill=DefaultValue("warn"),
                ),
                required=False,
            ),
        },
    )


rule_spec_cloudflare_ssl = CheckParameters(
    name="cloudflare_ssl",
    title=Title("Cloudflare SSL/TLS"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_ssl,
    condition=HostAndItemCondition(item_title=Title("Zone")),
)
