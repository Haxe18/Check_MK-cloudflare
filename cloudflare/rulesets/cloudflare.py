#!/usr/bin/env python3
"""Cloudflare special agent WATO configuration."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

from ..lib.constants import DEFAULT_CACHE_TTL, DEFAULT_DISCOVERY_TTL, DEFAULT_SERVICES


def _validate_ttl_multiple_of_60(value: int) -> None:
    """Validate that TTL is a multiple of 60 seconds.

    Args:
        value: TTL value in seconds.

    Raises:
        validators.ValidationError: If the TTL is not divisible by 60.
    """
    if value % 60 != 0:
        raise validators.ValidationError("TTL must be a multiple of 60 seconds")


def _validate_min_ttl(value: int) -> None:
    """Validate a minimum TTL of 60 seconds.

    Args:
        value: TTL value in seconds.

    Raises:
        validators.ValidationError: If the TTL is below 60 seconds.
    """
    if value < 60:
        raise validators.ValidationError("TTL must be at least 60 seconds")


def _valuespec_special_agents_cloudflare():
    """Build the special agent configuration form for Cloudflare.

    Returns:
        Dictionary: Ruleset parameter form specification.
    """
    return Dictionary(
        title=Title("Cloudflare Monitoring Configuration"),
        help_text=Help(
            "Configure monitoring of Cloudflare services including Zones, Zone Analytics, "
            "DNS Analytics, Workers, KV, R2, WAF, Rulesets, Access, Tunnels, "
            "Load Balancers, D1 Databases, SSL/TLS, and Pages."
        ),
        elements={
            "api_token": DictElement(
                parameter_form=Password(
                    title=Title("API Token"),
                    help_text=Help(
                        "Your Cloudflare API token. Create one at the Cloudflare dashboard "
                        "under Profile > API Tokens."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "account_id": DictElement(
                parameter_form=String(
                    title=Title("Account ID"),
                    help_text=Help(
                        "Your Cloudflare Account ID. Find it in the Cloudflare dashboard "
                        "under any zone's Overview page."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "services": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Services to Monitor"),
                    help_text=Help(
                        "Select which Cloudflare services to monitor. Each service requires "
                        "appropriate API permissions."
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="workers",
                            title=Title("Workers (Scripts, Analytics)"),
                        ),
                        MultipleChoiceElement(
                            name="kv",
                            title=Title("KV Namespaces"),
                        ),
                        MultipleChoiceElement(
                            name="zones",
                            title=Title("DNS Zones (Status)"),
                        ),
                        MultipleChoiceElement(
                            name="r2",
                            title=Title("R2 Buckets"),
                        ),
                        MultipleChoiceElement(
                            name="zone_analytics",
                            title=Title("Zone Analytics (Requests, Bandwidth, Threats)"),
                        ),
                        MultipleChoiceElement(
                            name="dns_analytics",
                            title=Title("DNS Analytics (Queries, Response Time)"),
                        ),
                        MultipleChoiceElement(
                            name="waf",
                            title=Title("WAF Events (Pro+ only)"),
                        ),
                        MultipleChoiceElement(
                            name="rulesets",
                            title=Title("Rulesets (Redirect, Cache, Config, Origin Rules)"),
                        ),
                        MultipleChoiceElement(
                            name="access",
                            title=Title("Cloudflare Access (Apps, Policies)"),
                        ),
                        MultipleChoiceElement(
                            name="tunnel",
                            title=Title("Cloudflare Tunnel"),
                        ),
                        MultipleChoiceElement(
                            name="load_balancer",
                            title=Title("Load Balancers (Pools, Origins)"),
                        ),
                        MultipleChoiceElement(
                            name="d1",
                            title=Title("D1 Databases"),
                        ),
                        MultipleChoiceElement(
                            name="ssl",
                            title=Title("SSL/TLS Status"),
                        ),
                        MultipleChoiceElement(
                            name="pages",
                            title=Title("Pages (Deployments, Functions)"),
                        ),
                    ],
                    prefill=DefaultValue(DEFAULT_SERVICES),
                ),
                required=True,
            ),
            "cache_ttl": DictElement(
                parameter_form=Integer(
                    title=Title("Metrics Cache TTL (seconds)"),
                    help_text=Help(
                        "Time-to-live for cached metrics data. Must be a multiple of 60. "
                        "Lower values provide fresher data but increase API calls."
                    ),
                    prefill=DefaultValue(DEFAULT_CACHE_TTL),
                    custom_validate=(
                        validators.NumberInRange(min_value=60),
                        _validate_ttl_multiple_of_60,
                    ),
                    unit_symbol="s",
                ),
                required=False,
            ),
            "discovery_ttl": DictElement(
                parameter_form=Integer(
                    title=Title("Discovery Cache TTL (seconds)"),
                    help_text=Help(
                        "Time-to-live for cached resource discovery data. Must be a multiple of 60 "
                        "and greater than or equal to the Metrics Cache TTL. Resource lists "
                        "(workers, zones, etc.) change less frequently than metrics."
                    ),
                    prefill=DefaultValue(DEFAULT_DISCOVERY_TTL),
                    custom_validate=(
                        validators.NumberInRange(min_value=60),
                        _validate_ttl_multiple_of_60,
                    ),
                    unit_symbol="s",
                ),
                required=False,
            ),
            "analytics_timeframe": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Analytics Timeframe"),
                    help_text=Help(
                        "Time range for analytics data collection. Shorter timeframes "
                        "provide more granular data but may show more variance."
                    ),
                    elements=[
                        SingleChoiceElement(name="t5m", title=Title("Last 5 minutes")),
                        SingleChoiceElement(name="t15m", title=Title("Last 15 minutes")),
                        SingleChoiceElement(name="t1h", title=Title("Last 1 hour")),
                        SingleChoiceElement(name="t6h", title=Title("Last 6 hours")),
                        SingleChoiceElement(name="t24h", title=Title("Last 24 hours")),
                    ],
                    prefill=DefaultValue("t24h"),
                ),
                required=False,
            ),
        },
    )


rule_spec_cloudflare = SpecialAgent(
    name="cloudflare",
    title=Title("Cloudflare"),
    topic=Topic.CLOUD,
    parameter_form=_valuespec_special_agents_cloudflare,
    help_text=Help(
        "This special agent monitors Cloudflare services via the Cloudflare API. "
        "It supports monitoring Zones, Zone Analytics, DNS Analytics, Workers, "
        "KV Namespaces, R2 Buckets, WAF Events, Rulesets, Access, Tunnels, "
        "Load Balancers, D1 Databases, SSL/TLS, and Pages."
    ),
)
