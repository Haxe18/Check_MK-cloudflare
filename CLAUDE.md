# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Check_MK (Checkmk) monitoring plugin for Cloudflare services. It uses the Cloudflare REST and GraphQL APIs to collect metrics and monitor various Cloudflare resources.

## Architecture

### Directory Structure

```
cloudflare/
├── lib/                    # Core library (special agent)
│   ├── constants.py        # Centralized constants (timeframes, TTLs, service names)
│   ├── client.py           # Cloudflare API client (REST + GraphQL)
│   ├── orchestrator.py     # Coordinates service sections
│   ├── base.py             # CloudflareSection abstract base class
│   ├── types.py            # Data classes (Resource, MetricResult, etc.)
│   ├── cache.py            # Caching layer (thread-safe APICounter)
│   ├── errors.py           # ErrorCollector for structured error handling (thread-safe)
│   ├── parallel.py         # Parallel execution utilities (ThreadPoolExecutor)
│   └── services/           # Service implementations (one per Cloudflare service)
├── agent_based/            # Check_MK check plugins (consume agent output)
├── rulesets/               # WATO configuration rules
├── server_side_calls/      # Special agent command generation
└── graphing/               # Metric graph definitions
```

### Data Flow

1. **Special Agent** (`lib/`) - Runs on Check_MK server, calls Cloudflare API
2. **Orchestrator** - Coordinates service sections, handles caching
3. **Service Sections** - Each service (workers, kv, zones, etc.) extends `CloudflareSection`
4. **Check Plugins** (`agent_based/`) - Parse agent output, generate checks and metrics

### Adding a New Service

1. Create `lib/services/newservice.py` - implement `CloudflareSection` (define `name`, `resource_type`, `metrics`, `discover_resources`, `fetch_analytics`)
2. Add API methods to `lib/client.py` if needed
3. Register in `lib/services/__init__.py` SECTION_REGISTRY
4. Create `agent_based/cloudflare_newservice.py` - check plugin
5. Create `rulesets/cloudflare_newservice.py` - WATO rules (see Ruleset Condition Types below)

### Ruleset Condition Types

Use the correct condition type based on whether the service has items:

```python
# Services OHNE Items (global pro Host):
# Beispiele: cloudflare_api_counter, cloudflare_workers_global
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

rule_spec = CheckParameters(
    name="cloudflare_example",
    title=Title("Cloudflare Example"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
    condition=HostCondition(),
)

# Services MIT Items (pro Service/Resource):
# Beispiele: cloudflare_kv, cloudflare_workers, cloudflare_zones
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

rule_spec = CheckParameters(
    name="cloudflare_example",
    title=Title("Cloudflare Example"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Example Item")),
)
```

**IMPORTANT:** `CheckParameterRulespecWithItem` does NOT exist in `cmk.rulesets.v1` API!

### Key Classes

- `CloudflareClient` - Wraps REST (`_rest_get`) and GraphQL (`_graphql_query`) APIs with retry logic
- `CloudflareSection` - Abstract base requiring `name`, `resource_type`, `metrics`, `discover_resources()`, `fetch_analytics()`
- `CloudflareOrchestrator` - Runs sections with two-tier caching (default discovery TTL: 1h, default metrics TTL: 5m; both configurable)
- `ErrorCollector` - Structured error collection with categories and services (thread-safe)
- `APICounter` - Tracks API request counts by type (thread-safe)

### Global Check Pattern (USAGE_RESOURCE_ID)

Services with account-wide usage limits use a special `_<service>_usage` resource alongside per-item resources:

```python
# In service section (e.g., services/d1.py):
USAGE_RESOURCE_ID = "_d1_usage"

def discover_resources(self):
    resources = []
    # Add global resource FIRST
    resources.insert(0, Resource(
        id=self.USAGE_RESOURCE_ID,
        name="D1 Global",
        resource_type="d1_global",
        metadata={...},
        available_metrics=["total_databases", "max_databases", ...],
    ))
    # Then add per-item resources
    for db in databases:
        resources.append(Resource(id=db["uuid"], name=db["name"], ...))
    return resources

# In check plugin (e.g., agent_based/cloudflare_d1.py):
USAGE_RESOURCE_ID = "_d1_usage"

def discover_cloudflare_d1(section):
    for resource_id, name in discover_cloudflare_resources_by_name(section, SERVICE_D1):
        if resource_id == USAGE_RESOURCE_ID:
            continue  # Skip global resource
        yield Service(item=name)

def discover_cloudflare_d1_global(section):
    for resource_id, _ in discover_cloudflare_resources_by_name(section, SERVICE_D1):
        if resource_id == USAGE_RESOURCE_ID:
            yield Service()  # No item - HostCondition()
            return
```

**Services using this pattern:** Workers (`_workers_usage`), D1 (`_d1_usage`), KV (`_kv_usage`), R2 (`_r2_usage`)

### Centralized Constants (`lib/constants.py`)

All magic numbers and repeated strings are centralized in `constants.py`.

**IMPORTANT:** In `agent_based` plugins and `rulesets`, you MUST use relative imports (e.g., `from ..lib.constants`) because the `cloudflare` package is not available in the Check_MK agent context.

```python
from ..lib.constants import (
    # Cache/Timeout
    DEFAULT_CACHE_TTL,          # 300 (5 minutes)
    DEFAULT_DISCOVERY_TTL,      # 3600 (1 hour)
    DEFAULT_REQUEST_TIMEOUT,    # 30 seconds
    DEFAULT_MAX_RETRIES,        # 3
    DEFAULT_MAX_WORKERS,        # 8 (parallel API calls)

    # Timeframes
    TIMEFRAME_5M, TIMEFRAME_15M, TIMEFRAME_1H, TIMEFRAME_6H, TIMEFRAME_24H,
    DEFAULT_TIMEFRAME,          # "24h"
    TIMEFRAME_MINUTES,          # {"5m": 5, "15m": 15, ...}
    WATO_TIMEFRAME_MAP,         # {"t5m": "5m", ...} for WATO -> agent conversion

    # API
    CLOUDFLARE_API_BASE_URL,    # "https://api.cloudflare.com/client/v4"
    CLOUDFLARE_GRAPHQL_URL,     # "https://api.cloudflare.com/client/v4/graphql"
    ENDPOINT_TYPE_DEFAULT,      # "default"
    ENDPOINT_TYPE_GRAPHQL,      # "graphql"

    # Service Names
    SERVICE_WORKERS, SERVICE_KV, SERVICE_ZONES, SERVICE_R2,
    SERVICE_ZONE_ANALYTICS, SERVICE_DNS_ANALYTICS, SERVICE_WAF,
    SERVICE_RULESETS, SERVICE_ACCESS, SERVICE_TUNNEL,
    SERVICE_LOAD_BALANCER, SERVICE_D1, SERVICE_SSL, SERVICE_PAGES,
    DEFAULT_SERVICES,           # ["zones", "zone_analytics", "dns_analytics"]

    # Error Categories
    ERROR_CATEGORY_API,         # "api"
    ERROR_CATEGORY_DISCOVERY,   # "discovery"
    ERROR_CATEGORY_METRICS,     # "metrics"
    ERROR_CATEGORY_CACHE,       # "cache"
    ERROR_SERVICE_REST,         # "rest"
    ERROR_SERVICE_GRAPHQL,      # "graphql"

    # D1 Plan Limits
    D1_FREE_MAX_DATABASES,      # 10
    D1_FREE_DAILY_ROWS_READ,    # 5_000_000
    D1_FREE_DAILY_ROWS_WRITTEN, # 100_000
    D1_FREE_MAX_STORAGE,        # 5 GB
    D1_PAID_MAX_DATABASES,      # 50_000
    D1_PAID_MONTHLY_ROWS_READ,  # 0 (usage-based monitoring semantics)
    D1_PAID_MONTHLY_ROWS_WRITTEN, # 0 (usage-based monitoring semantics)
    D1_PAID_MAX_STORAGE,        # 0 (usage-based monitoring semantics)

    # KV Plan Limits
    KV_FREE_DAILY_READS,        # 100_000
    KV_FREE_DAILY_WRITES,       # 1_000
    KV_FREE_DAILY_DELETES,      # 1_000
    KV_FREE_DAILY_LISTS,        # 1_000
    KV_FREE_MAX_STORAGE,        # 1 GB
    KV_PAID_MONTHLY_READS,      # 0 (usage-based monitoring semantics)
    KV_PAID_MONTHLY_WRITES,     # 0 (usage-based monitoring semantics)

    # R2 Plan Limits
    R2_FREE_STORAGE,            # 10 GB
    R2_FREE_CLASS_A_OPS,        # 1_000_000
    R2_FREE_CLASS_B_OPS,        # 10_000_000
    R2_PAID_STORAGE,            # 0 (unlimited/pay-per-use)

    # Other
    STATE_MAP,                  # {"ok": 0, "warn": 1, "crit": 2}
    FREE_PLAN_DAILY_LIMIT,      # 100000
    CACHE_PREFIX_DISCOVERY,     # "discovery"
    CACHE_PREFIX_METRICS,       # "metrics"
)
```

**Usage:** Import constants instead of using magic numbers or strings directly. This ensures consistency and makes values easy to change globally.

**Important:** `DEFAULT_TIMEFRAME` (`"24h"`) is separate from cache TTL settings. The 5-minute value is the default metrics cache TTL, not the default analytics timeframe.

### Parallel Execution

The client uses `ThreadPoolExecutor` for parallel API calls to improve performance. This is implemented in `lib/parallel.py`.

**Parallelized Methods:**
- `fetch_workers_analytics` - fetches per-worker analytics in parallel
- `fetch_kv_analytics` - fetches per-namespace analytics (2 queries each)
- `fetch_kv_read_status` - fetches per-namespace read status
- `fetch_kv_monthly_summary` - fetches per-namespace monthly summary
- `fetch_zone_analytics` - fetches per-zone analytics
- `fetch_dns_analytics` - fetches per-zone DNS analytics
- `fetch_waf_analytics` - fetches per-zone WAF analytics
- `fetch_pages_functions_analytics` - fetches per-project analytics

**Thread Safety:**
- `ErrorCollector` uses `threading.Lock()` to protect error list access
- `APICounter` uses `threading.Lock()` to protect counter increments
- `requests.request()` is thread-safe by design

**Performance Impact:**
| Scenario | Sequential | Parallel | Speedup |
|----------|-----------|----------|---------|
| 10 Workers | ~10-20s | ~1-2s | 10x |
| 10 KV Namespaces | ~20-40s | ~2-4s | 10x |
| 10 Zones | ~10-20s | ~1-2s | 10x |

**Rate Limiting:**
- Cloudflare allows ~200 requests / 30 seconds
- Default `max_workers=8` is safe under this limit
- Each method respects this by using `parallel_map()` with configurable workers

**Usage Example:**
```python
from .parallel import parallel_map

def fetch_method(self, items: list[str]) -> dict[str, Any]:
    def fetch_single(item: str) -> dict[str, Any]:
        # API call logic here
        return result

    results = parallel_map(fetch_single, items, logger=self)
    return {k: v if v is not None else {} for k, v in results.items()}
```

## Available Services

workers, kv, zones, r2, zone_analytics, dns_analytics, waf, rulesets, access, tunnel, load_balancer, d1, ssl, pages

## Packaging

Build .mkp package:
```bash
# Build MKP package (requires Check_MK-plugin_mpk_action repo)
../Check_MK-plugin_mpk_action/scripts/build_plugin.sh \
  --plugin-name cloudflare \
  --title "Cloudflare Monitoring" \
  --description "Cloudflare Monitoring Plugin - monitors Cloudflare usage/metrics." \
  --version 1.0.0
```

The plugin is uploaded via Check_MK WATO "Extension Packages" page.

## API Notes

- Uses Bearer token authentication
- GraphQL endpoint at `https://api.cloudflare.com/client/v4/graphql`
- Timeframes: 5m, 15m, 1h, 6h, 24h
- Performance metrics (TTFB, origin response) require Pro+ plans

## Cloudflare API Documentation

### GraphQL Analytics API
- Main docs: https://developers.cloudflare.com/analytics/graphql-api/
- Schema exploration: https://developers.cloudflare.com/analytics/graphql-api/getting-started/explore-graphql-schema/
- Datasets reference: https://developers.cloudflare.com/analytics/graphql-api/features/data-sets/
- API limits: https://developers.cloudflare.com/analytics/graphql-api/limits/

### DNS Analytics
- DNS analytics overview: https://developers.cloudflare.com/dns/additional-options/analytics/
- DNS API properties: https://developers.cloudflare.com/dns/reference/analytics-api-properties/
- Foundation DNS GraphQL: https://developers.cloudflare.com/dns/foundation-dns/graphql-analytics/

### Timing Insights (Performance Metrics)
- Blog post with field names: https://blog.cloudflare.com/introducing-timing-insights/
- Migration guide: https://developers.cloudflare.com/analytics/graphql-api/migration-guides/graphql-api-analytics/

### Service Limits & Pricing
- Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
- KV limits: https://developers.cloudflare.com/kv/platform/limits/
- KV pricing: https://developers.cloudflare.com/kv/platform/pricing/
- D1 limits: https://developers.cloudflare.com/d1/platform/limits/
- D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/
- R2 limits: https://developers.cloudflare.com/r2/platform/limits/
- R2 pricing: https://developers.cloudflare.com/r2/pricing/

### Unofficial Schema Documentation
- Schema explorer: https://cfdata.lol/graphql/
- Schema docs: https://pages.johnspurlock.com/graphql-schema-docs/cloudflare.html

### Important Field Name Notes

**Zone Analytics Data Collection (`httpRequests1hGroups`):**
- **Hourly Bucketing:** Basic metrics (requests, bytes, threats) are aggregated in 1-hour buckets aligned to the hour (HH:00).
- **Timeframe Logic:** If the query `since` parameter is later than the start of the current hour (e.g. requesting last 5m at 10:15), Cloudflare's API excludes the current hour's bucket entirely.
- **Client Adjustment:** To fix this, `fetch_zone_analytics` automatically adjusts `since` to `current_hour - 1s` when necessary. This ensures the current incomplete bucket is returned.
- **Pro+ Zones:** These zones run two queries:
  1. `httpRequests1hGroups` with adjusted time (for basic counters)
  2. `httpRequestsAdaptiveGroups` with precise time (for performance quantiles)

**Zone Analytics (`httpRequestsAdaptiveGroups`):**
- Quantiles use `Ms` suffix: `edgeTimeToFirstByteMsP50`, `originResponseDurationMsP50`, `edgeDnsResponseTimeMsP50`
- Performance metrics (TTFB, origin response) require Pro+ plans
- Code auto-detects plan from `resource.metadata["plan"]` and skips Pro+ query for Free zones

**DNS Analytics (`dnsAnalyticsAdaptiveGroups`):**
- Only supports `count` and `dimensions { responseCode }` fields
- NO `avg` or `quantiles` fields available (contrary to REST API)
- Response time metrics are NOT available via GraphQL
- Available metrics: `query_count`, `noerror_count`, `nxdomain_count`, `servfail_count`

**Workers Analytics (`workersInvocationsAdaptive`):**
- All timing quantiles are in **microseconds** - must divide by 1000 for milliseconds
- Available quantile fields:
  - `cpuTimeP50/P90/P99/P999` - CPU execution time
  - `wallTimeP50/P90/P99/P999` - Wall time (includes ctx.waitUntil)
  - `requestDurationP50/P90/P99/P999` - Request duration (response time)
- **IMPORTANT**: `durationP50` is NOT the same as Request Duration - use `requestDurationP50`!
- Wall Time vs Request Duration:
  - Wall Time: Total time until JavaScript context closes (includes waitUntil handlers)
  - Request Duration: Time until response is sent to client (like in Cloudflare Dashboard)

**Pages Functions Analytics (`pagesFunctionsInvocationsAdaptiveGroups`):**
- Only supports **P50 and P99** quantiles (NO P90, P95, P999!)
- Available quantile fields:
  - `cpuTimeP50` - CPU execution time (median)
  - `cpuTimeP99` - CPU execution time (99th percentile)
- Timing values are in **microseconds** - must divide by 1000 for milliseconds
- Filter by `scriptName` (project name)

**D1 Analytics (`d1AnalyticsAdaptiveGroups`):**
- Uses `d1AnalyticsAdaptiveGroups` node
- Available metrics: `rowsRead`, `rowsWritten`, `readQueries`, `writeQueries` (sum), and `queryBatchTimeMs` (avg)

**R2 Storage Analytics (`r2StorageAdaptiveGroups`):**
- Uses `r2StorageAdaptiveGroups` node
- Metrics: `payloadSize` (storage), `objectCount`
- **Important**: These are snapshot metrics. The plugin forces a 24h query window to ensure the latest snapshot is found, as they may not appear in shorter windows.

## Error Handling

### Error Constants

Use centralized error constants instead of hardcoded strings:

```python
from ..lib.constants import (
    ERROR_CATEGORY_API,
    ERROR_CATEGORY_DISCOVERY,
    ERROR_SERVICE_REST,
    ERROR_SERVICE_GRAPHQL,
)

# Adding errors:
self.error_collector.add(ERROR_CATEGORY_API, ERROR_SERVICE_REST, "Permission denied")
```

### ErrorCollector Class (`lib/errors.py`)

Errors are collected using a structured `ErrorCollector` class (similar to AWS CloudWatch plugin):

```python
from .errors import ErrorCollector

# In CloudflareClient.__init__():
self.error_collector = ErrorCollector()

# Adding errors:
self.error_collector.add("api", "rest", "Permission denied: workers/scripts")
self.error_collector.add("api", "graphql", "Rate limit exceeded")

# Getting errors:
errors = self.error_collector.get_and_clear()  # Returns list[dict] and clears
```

**CloudflareError Structure:**
```python
{
    "category": "api",       # "api", "discovery", "metrics", "cache"
    "service": "workers",    # Service name or "rest"/"graphql" for client errors
    "message": "Error text",
    "timestamp": 1734180000.0
}
```

**ErrorCollector Methods:**
- `add(category, service, message)` - Add a structured error
- `has_errors()` - Returns True if any errors collected
- `count()` - Returns number of errors
- `to_list()` - Returns list of error dicts
- `get_and_clear()` - Returns list of error dicts and clears collection
- `summary()` - Returns summary like "2 api, 1 discovery"
- `brief(max_items=3)` - Returns affected services like "workers, kv, ..."

### Error Categories

| Category | Description |
|----------|-------------|
| `api` | REST/GraphQL API errors (permission, rate limit, HTTP errors) |
| `discovery` | Resource discovery errors (unknown service, missing resources) |
| `metrics` | Metrics collection errors (failed analytics fetch) |
| `cache` | Cache-related errors |

### Error Flow

1. `CloudflareClient.error_collector` collects all REST/GraphQL API errors
2. `CloudflareOrchestrator.run()` collects errors via `client.get_and_clear_errors()`
3. Errors appear in `CloudflareErrors` array in agent output (as list of dicts)
4. `check_cloudflare_api_counter` displays errors with category summary

**Check_MK Display:**
- Summary: `Errors: 2 api, 1 discovery`
- Details: `[api/rest] Permission denied: workers/scripts`

### REST API Error Handling

REST API errors (including 403 permission errors) are collected with category "api" and service "rest":

1. `_rest_get()` adds errors via `self.error_collector.add("api", "rest", ...)`
2. Permission errors (403) include helpful hints about required permissions
3. Errors appear in `CloudflareErrors` array in agent output

Example error message:
```
Permission denied: zones/xxx/settings/ssl (needs 'Zone > Zone Settings > Read')
```

### Permission Hints

The client includes hints for common endpoints showing where to set permissions in Cloudflare dashboard:

| Endpoint Pattern | Required Permission |
|------------------|---------------------|
| `settings/ssl` | Zone > Zone Settings > Read |
| `security/events` | Zone > Firewall Services > Read |
| `dns_records` | Zone > DNS > Read |
| `rulesets` | Zone > Config Rules > Read |
| `d1/database` | Account > D1 > Read |
| `workers/scripts` | Account > Worker Scripts > Read |
| `storage/kv/namespaces` | Account > Workers KV Storage > Read |
| `r2/buckets` | Account > Workers R2 Storage > Read |
| `access/apps` | Account > Access: Apps and Policies > Read |
| `cfd_tunnel` | Account > Cloudflare Tunnel > Read |
| `load_balancers` | Account > Load Balancers > Read |
| `subscriptions` | Account > Billing > Read |
| `pages/projects` | Account > Cloudflare Pages > Read |

### Ignoring Specific Errors

Users can configure the "Cloudflare API Usage" check to ignore specific errors via WATO:

- **Ruleset:** `cloudflare/rulesets/cloudflare_api_counter.py`
- **Parameter:** `ignore_error_patterns` - List of substrings to match (NO regex support)
- **Example:** Adding `does not have permission` ignores all permission errors

Ignored errors:
- Do not trigger WARN state
- Are shown separately in check output as "Ignored: X"
- Still appear in check details for visibility

## Cache Status Display

The agent output includes Check_MK cache metadata so users see cache info in the GUI:

```
<<<cloudflare:sep(0):cached(1734180000,300)>>>
```

- `1734180000` = Unix timestamp when data was fetched
- `300` = Cache TTL in seconds (matches `--cache-ttl` argument)

Check_MK automatically displays: "Cache vor X s erstellt, Cache-Intervall: 5 m"

**Important:** The order must be `sep(0):cached(...)` - NOT `cached(...):sep(0)`

## Metrics Best Practices

### Always Output Metrics (Even When Zero)

For continuous line graphs in Check_MK, metrics should ALWAYS be yielded:

```python
# BAD - creates gaps in graphs (n/a values)
if cpu_p50 > 0:
    yield Metric("cloudflare_worker_cpu_p50", cpu_p50)

# GOOD - continuous line graphs
yield Metric("cloudflare_worker_cpu_p50", cpu_p50)
```

The `if > 0:` pattern should only be used for summary text, not for metrics.

## Check_MK API Constraints

### Global Free-Tier Monitoring Parameter

For global usage checks (`workers_global`, `kv_global`, `d1_global`, `r2_global`), use:

- `free_tier_monitoring: bool` (default `True`)
- No legacy string values (`enabled/disabled`) and no fallback keys
- Scope is limited to free-tier/included-tier percentage checks only
- Absolute/fixed thresholds in other checks are unaffected

### Check Function `params` Argument

**IMPORTANT:** When `check_default_parameters` is set (not None), the check function MUST have a parameter named exactly `params`:

```python
# CORRECT - parameter named 'params'
def check_cloudflare_example(
    item: str,
    params: dict[str, Any],  # pylint: disable=unused-argument
    section: dict[str, Any],
) -> CheckResult:
    ...

check_plugin = CheckPlugin(
    ...
    check_default_parameters={},  # Not None, so 'params' is required
)

# WRONG - '_params' causes TypeError
def check_cloudflare_example(
    item: str,
    _params: dict[str, Any],  # Will fail validation!
    ...
)
```

Error message: `TypeError: check_function: 'params' argument expected if and only if default parameters are not None`

## Helper Functions

### `create_metric()` (types.py)

Use this helper to create MetricResult objects with consistent metadata:

```python
from ..types import create_metric

# Simple metric (name from resource automatically added)
results.append(create_metric(
    resource, "requests", float(count), "Count", "sum", timeframe))

# With extra metadata
results.append(create_metric(
    resource, "status", status_value, "Status", "gauge", timeframe,
    extra_metadata={"status_text": status}))
```

### `_discover_zones()` (base.py)

Zone-based services can use this helper in CloudflareSection subclasses:

```python
def discover_resources(self) -> list[Resource]:
    return self._discover_zones()  # Basic zone discovery

def discover_resources(self) -> list[Resource]:
    return self._discover_zones(include_plan=True)  # Include plan info for Pro+ detection
```

### Check Plugin Helpers (cloudflare_helpers.py)

**Discovery with names** - All check plugins use human-readable names as service items:

```python
from .cloudflare_helpers import (
    SERVICE_KV,
    collect_metrics_for_resource,
    discover_cloudflare_resources_by_name,
    get_resource_id_by_name,
)

def discover_cloudflare_kv(section: dict[str, Any]) -> DiscoveryResult:
    for _resource_id, resource_name in discover_cloudflare_resources_by_name(section, SERVICE_KV):
        yield Service(item=resource_name)  # Name as item, not ID

def check_cloudflare_kv(item: str, params: dict[str, Any], section: dict[str, Any]) -> CheckResult:
    # Look up resource ID by name for metric collection
    resource_id = get_resource_id_by_name(section, SERVICE_KV, item)
    if not resource_id:
        yield Result(state=State.UNKNOWN, summary="Not found")
        return

    metrics = collect_metrics_for_resource(section, SERVICE_KV, resource_id)
    # ... rest of check
```

**Helper functions:**
- `discover_cloudflare_resources_by_name(section, service)` - Yields `(resource_id, resource_name)` tuples
- `get_resource_id_by_name(section, service, name)` - Returns resource ID for a given name (for metric lookup)
- `collect_metrics_for_resource(section, service, resource_id)` - Collects metrics by ID
- `get_resource_metadata(section, service, resource_id)` - Gets resource metadata by ID

**Generic usage limit check** - Eliminates repetitive limit-checking code across global checks:

```python
from .cloudflare_helpers import check_usage_limit

# In check function:
yield from check_usage_limit(
    usage=current_value,         # e.g., 3_500_000
    limit=plan_limit,            # e.g., 5_000_000 (0 = unlimited)
    label="Rows Read",           # Human-readable label
    metric_usage="cloudflare_d1_daily_rows_read",
    metric_limit="cloudflare_d1_rows_read_limit",
    metric_percent="cloudflare_d1_rows_read_usage_percent",
    params=params,
    param_key="rows_read_usage_levels",
    render_func=format_count,    # or format_bytes for storage
    default_warn=80.0,
    default_crit=95.0,
)
# Yields: Result (with state based on %), Metric (usage), Metric (limit), Metric (percent)
```
