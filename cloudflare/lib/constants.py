#!/usr/bin/env python3
"""Constants for Cloudflare monitoring.

This module centralizes all constants used throughout the Cloudflare plugin
to ensure consistency and easy maintenance.
"""

# =============================================================================
# State Mapping for Check_MK
# =============================================================================

# Mapping from SingleChoice string values to Check_MK State enum integers
STATE_MAP = {"ok": 0, "warn": 1, "crit": 2}

# =============================================================================
# Cache and Timeout Constants
# =============================================================================

# Default metrics cache TTL (5 minutes)
DEFAULT_CACHE_TTL = 300

# Default discovery cache TTL (1 hour)
DEFAULT_DISCOVERY_TTL = 3600

# Default request timeout in seconds
DEFAULT_REQUEST_TIMEOUT = 10

# Default maximum retries for failed requests
DEFAULT_MAX_RETRIES = 3

# Longest wait (seconds) before retrying a rate-limited (HTTP 429) request;
# if Cloudflare asks for a longer wait, the request is not retried
RATE_LIMIT_MAX_WAIT = 10

# Time (seconds) after which one agent run starts no more API requests. Later requests
# (and retries) fail right away as temporary errors, so the agent can still answer
# before Checkmk's special agent timeout (60s) and serve the last good data. A request
# already running is not cut short, it ends after its own timeout
AGENT_TIME_BUDGET = 45

# Most pages read from one paginated REST list (guards against endless paging)
REST_MAX_PAGES = 100

# Default max workers for parallel API calls
# Cloudflare rate limits: ~200 requests / 30 seconds = ~6.7 req/s
# Using 8 workers is safe and provides good parallelism
DEFAULT_MAX_WORKERS = 8

# =============================================================================
# Timeframe Constants
# =============================================================================

# Available timeframes
TIMEFRAME_5M = "5m"
TIMEFRAME_15M = "15m"
TIMEFRAME_1H = "1h"
TIMEFRAME_6H = "6h"
TIMEFRAME_24H = "24h"

# Default analytics timeframe
DEFAULT_TIMEFRAME = "24h"

# Timeframe to minutes mapping
TIMEFRAME_MINUTES = {
    TIMEFRAME_5M: 5,
    TIMEFRAME_15M: 15,
    TIMEFRAME_1H: 60,
    TIMEFRAME_6H: 360,
    TIMEFRAME_24H: 1440,
}

# Map WATO timeframe values (with 't' prefix) to agent values
WATO_TIMEFRAME_MAP = {
    "t5m": TIMEFRAME_5M,
    "t15m": TIMEFRAME_15M,
    "t1h": TIMEFRAME_1H,
    "t6h": TIMEFRAME_6H,
    "t24h": TIMEFRAME_24H,
}

# =============================================================================
# API Constants
# =============================================================================

# Cloudflare API base URLs
CLOUDFLARE_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CLOUDFLARE_GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"

# Cloudflare API error code 9109: "Unauthorized to access requested resource" for a
# missing permission, "Invalid access token" for an invalid token
CLOUDFLARE_ERROR_CODE_UNAUTHORIZED = 9109

# Cloudflare API error codes sent when the token lacks a permission:
# 10000 "Authentication error" (also sent for an invalid token), 9109 (see above)
CLOUDFLARE_PERMISSION_ERROR_CODES = (10000, CLOUDFLARE_ERROR_CODE_UNAUTHORIZED)

# API endpoint types for rate limiting
ENDPOINT_TYPE_DEFAULT = "default"
ENDPOINT_TYPE_GRAPHQL = "graphql"

# =============================================================================
# Service Name Constants
# =============================================================================

SERVICE_WORKERS = "workers"
SERVICE_KV = "kv"
SERVICE_ZONES = "zones"
SERVICE_R2 = "r2"
SERVICE_ZONE_ANALYTICS = "zone_analytics"
SERVICE_DNS_ANALYTICS = "dns_analytics"
SERVICE_WAF = "waf"
SERVICE_RULESETS = "rulesets"
SERVICE_ACCESS = "access"
SERVICE_TUNNEL = "tunnel"
SERVICE_LOAD_BALANCER = "load_balancer"
SERVICE_D1 = "d1"
SERVICE_SSL = "ssl"
SERVICE_PAGES = "pages"

# Default services to monitor
DEFAULT_SERVICES = [SERVICE_ZONES, SERVICE_ZONE_ANALYTICS, SERVICE_DNS_ANALYTICS]

# =============================================================================
# Error Category Constants
# =============================================================================

ERROR_CATEGORY_API = "api"
ERROR_CATEGORY_DISCOVERY = "discovery"
ERROR_CATEGORY_METRICS = "metrics"
ERROR_CATEGORY_CACHE = "cache"

# Error service identifiers for client-level errors
ERROR_SERVICE_REST = "rest"
ERROR_SERVICE_GRAPHQL = "graphql"

# =============================================================================
# Cache Prefix Constants
# =============================================================================

CACHE_PREFIX_DISCOVERY = "discovery"
CACHE_PREFIX_METRICS = "metrics"

# =============================================================================
# Workers Plan Limits
# =============================================================================

# Workers Free Plan daily request limit
FREE_PLAN_DAILY_LIMIT = 100000

# =============================================================================
# D1 Plan Limits
# =============================================================================

# D1 Free Plan limits (daily)
D1_FREE_MAX_DATABASES = 10
D1_FREE_DAILY_ROWS_READ = 5_000_000  # 5M rows/day
D1_FREE_DAILY_ROWS_WRITTEN = 100_000  # 100K rows/day
D1_FREE_MAX_STORAGE = 5 * 1024 * 1024 * 1024  # 5 GB

# D1 Paid/Bundled plan limits for monitoring semantics:
# - Database count has a practical account cap
# - Storage/row allowances are usage-based and should not be treated as hard caps
D1_PAID_MAX_DATABASES = 50_000
D1_PAID_MONTHLY_ROWS_READ = 0  # Usage-based/included allowance (no hard limit alert)
D1_PAID_MONTHLY_ROWS_WRITTEN = 0  # Usage-based/included allowance (no hard limit alert)
D1_PAID_MAX_STORAGE = 0  # Usage-based/included allowance (no hard limit alert)

# =============================================================================
# KV Plan Limits
# =============================================================================

# KV Free Plan limits (daily)
KV_FREE_DAILY_READS = 100_000  # 100K reads/day
KV_FREE_DAILY_WRITES = 1_000  # 1K writes/day
KV_FREE_DAILY_DELETES = 1_000  # 1K deletes/day
KV_FREE_DAILY_LISTS = 1_000  # 1K lists/day
KV_FREE_MAX_STORAGE = 1 * 1024 * 1024 * 1024  # 1 GB

# KV Paid/Bundled plan limits for monitoring semantics:
# operation and storage values are included allowances, not hard caps
KV_PAID_MONTHLY_READS = 0  # Usage-based/included allowance (no hard limit alert)
KV_PAID_MONTHLY_WRITES = 0  # Usage-based/included allowance (no hard limit alert)
KV_PAID_MONTHLY_DELETES = 0  # Usage-based/included allowance (no hard limit alert)
KV_PAID_MONTHLY_LISTS = 0  # Usage-based/included allowance (no hard limit alert)
KV_PAID_MAX_STORAGE = 0  # Usage-based/included allowance (no hard limit alert)

# =============================================================================
# R2 Plan Limits
# =============================================================================

# R2 Free Plan limits (monthly, same for all plans - free tier included)
R2_FREE_STORAGE = 10 * 1024 * 1024 * 1024  # 10 GB/month
R2_FREE_CLASS_A_OPS = 1_000_000  # 1M Class A ops/month (writes)
R2_FREE_CLASS_B_OPS = 10_000_000  # 10M Class B ops/month (reads)

# R2 Paid Plan: pay-per-use, no hard limits (0 = unlimited for monitoring)
R2_PAID_STORAGE = 0  # Unlimited (pay-per-use)
R2_PAID_CLASS_A_OPS = 0  # Unlimited
R2_PAID_CLASS_B_OPS = 0  # Unlimited

# =============================================================================
# R2 Jurisdictions
# =============================================================================

# Supported R2 Jurisdictions
# None = Default/Global (US)
# "eu" = European Union
R2_JURISDICTIONS = [None, "eu"]
