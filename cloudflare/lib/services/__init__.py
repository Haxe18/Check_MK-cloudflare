#!/usr/bin/env python3
# pylint: disable=wrong-import-position
"""Service section registry for Cloudflare monitoring."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import CloudflareSection

from ..constants import DEFAULT_SERVICES
from .access import AccessSection
from .d1 import D1Section
from .dns_analytics import DNSAnalyticsSection
from .kv import KVSection
from .load_balancer import LoadBalancerSection
from .pages import PagesSection
from .r2 import R2Section
from .rulesets import RulesetsSection
from .ssl import SSLSection
from .tunnel import TunnelSection
from .waf import WAFSection
from .workers import WorkersSection
from .zone_analytics import ZoneAnalyticsSection
from .zones import ZonesSection

# Registry mapping service names to section classes
SECTION_REGISTRY: dict[str, type["CloudflareSection"]] = {
    "workers": WorkersSection,
    "kv": KVSection,
    "zones": ZonesSection,
    "r2": R2Section,
    "zone_analytics": ZoneAnalyticsSection,
    "dns_analytics": DNSAnalyticsSection,
    "waf": WAFSection,
    "rulesets": RulesetsSection,
    "access": AccessSection,
    "tunnel": TunnelSection,
    "load_balancer": LoadBalancerSection,
    "d1": D1Section,
    "ssl": SSLSection,
    "pages": PagesSection,
}

# All available services
ALL_SERVICES = list(SECTION_REGISTRY.keys())

__all__ = [
    "SECTION_REGISTRY",
    "DEFAULT_SERVICES",
    "ALL_SERVICES",
    "WorkersSection",
    "KVSection",
    "ZonesSection",
    "R2Section",
    "ZoneAnalyticsSection",
    "DNSAnalyticsSection",
    "WAFSection",
    "RulesetsSection",
    "AccessSection",
    "TunnelSection",
    "LoadBalancerSection",
    "D1Section",
    "SSLSection",
    "PagesSection",
]
