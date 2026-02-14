#!/usr/bin/env python3
"""Cloudflare DNS Zones check parameters ruleset."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_cloudflare_zones() -> Dictionary:
    """Build the parameter form for DNS zone status checks.

    Returns:
        Dictionary: Check parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare DNS Zones Thresholds"),
        help_text=Help("Configure thresholds for Cloudflare DNS Zones monitoring."),
        elements={
            "state_paused": DictElement(
                parameter_form=SingleChoice(
                    title=Title("State if zone is paused"),
                    elements=[
                        SingleChoiceElement(name="ok", title=Title("OK")),
                        SingleChoiceElement(name="warn", title=Title("WARN")),
                        SingleChoiceElement(name="crit", title=Title("CRIT")),
                    ],
                    prefill=DefaultValue("warn"),
                ),
                required=False,
            ),
            "state_not_active": DictElement(
                parameter_form=SingleChoice(
                    title=Title("State if zone is not active"),
                    elements=[
                        SingleChoiceElement(name="ok", title=Title("OK")),
                        SingleChoiceElement(name="warn", title=Title("WARN")),
                        SingleChoiceElement(name="crit", title=Title("CRIT")),
                    ],
                    prefill=DefaultValue("warn"),
                ),
                required=False,
            ),
        },
    )


rule_spec_cloudflare_zones = CheckParameters(
    name="cloudflare_zones",
    title=Title("Cloudflare DNS Zones"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_cloudflare_zones,
    condition=HostAndItemCondition(item_title=Title("Zone")),
)
