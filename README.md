# Check_MK Cloudflare Monitoring

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)

Comprehensive Cloudflare monitoring for CheckMK using the Cloudflare REST and GraphQL APIs.

## Features

- **14 Cloudflare Services**: Zones, Workers, KV, R2, D1, SSL, Tunnels, WAF, Rulesets, Access, Load Balancers, Pages, and more
- **REST + GraphQL API**: Uses both APIs for optimal data collection
- **Parallel API Calls**: 6-15x faster data collection using ThreadPoolExecutor
- **Two-Tier Caching**: Discovery TTL (default: 1 hour) and Metrics TTL (default: 5 minutes), both configurable
- **Smart Cache Invalidation**: Cache auto-invalidates when service configuration changes
- **Complete Resource Lists**: Paginated API lists (zones, KV namespaces, tunnels, Access apps, Pages projects, R2 buckets, D1 databases, load balancer pools) are read page by page
- **Transient Error Protection**: When a temporary API error occurs (HTTP 5xx, rate limit, timeout, network, invalid JSON response, GraphQL "try again" errors, failed discovery), the last good data is shown instead of empty or zeroed values, as long as it is not older than the discovery cache TTL (at least twice the cache TTL; 1 hour by default). The API is retried at the normal cache interval. Lasting errors such as missing permissions are cached as usual. 45 seconds into an agent run no more API requests are started; the remaining ones count as temporary errors, so the agent can still answer within Checkmk's timeout
- **Token Not in the Process List**: Checkmk passes the API token as a password store reference
- **Pro+ Plan Detection**: Automatically enables performance metrics (TTFB, Origin Response Time) for Pro+ zones
- **Unused Permission Hints**: Shows which API permissions can be removed (no resources found)
- **API Error Tracking**: Surface permission errors and API issues in CheckMK
- **Configurable Alerting**: Optional thresholds via WATO rules
- **SimpleLevels Threshold Model**: Thresholds use CheckMK SimpleLevels format (no legacy parameter format support)

## Supported Services

| Service | Description | Key Metrics |
|---------|-------------|-------------|
| **Zones** | DNS Zone Status | status, paused |
| **Zone Analytics** | HTTP Traffic Analytics | requests, bandwidth, threats, cache_hit_ratio, TTFB* |
| **DNS Analytics** | DNS Query Analytics | query_count, noerror, nxdomain, servfail |
| **Workers** | Workers Scripts | requests, errors, cpu_time, duration, subrequests |
| **Workers Global** | Workers Free Tier Monitoring | daily_requests, daily_limit, usage_percent |
| **KV** | KV Namespaces | reads, writes, deletes, storage, latency quantiles |
| **KV Global** | KV Free Tier Monitoring | daily_reads, writes, deletes, lists vs included free tier |
| **R2** | R2 Storage Buckets | location, storage, object_count |
| **R2 Global** | R2 Usage vs Included Free Tier | total_storage vs included free tier |
| **WAF** | Security Events | total_events, blocked, challenged |
| **Rulesets** | Zone Rulesets (Redirect, Cache, Config, Origin) | ruleset_count, number of redirect, cache, config, origin rules |
| **Tunnel** | Cloudflare Tunnel | status, connection_count |
| **Access** | Access Applications | policy_count, allowed_idps |
| **Load Balancer** | Load Balancer Pools | healthy, origin_count, healthy_origins, health_rtt |
| **D1** | D1 Databases | database_count, storage, queries, rows_read, rows_written, duration |
| **D1 Global** | D1 Free Tier Monitoring | databases, storage, rows_read, rows_written vs included free tier |
| **SSL** | SSL/TLS Encryption Mode (certificates are not checked) | ssl_mode (off = WARN, not readable = UNKNOWN) |
| **Pages** | Cloudflare Pages | deployment_status, deployment_age, functions_invocations* |

**Note:** Account-wide usage/limit metrics are shown in the corresponding **\* Global** services (Workers, KV, D1, R2), not in per-resource services.

*\* TTFB, Origin Response Time, and Edge DNS metrics require Pro+ plan*
*\* Pages Functions metrics only available for projects with Functions enabled*

## Required Cloudflare Permissions

Create an API Token with the following permissions:

| Type | Permission | Access | Required For |
|------|------------|--------|--------------|
| Zone | Zone  | Read | All zone-based services |
| Zone | Analytics | Read | Zone Analytics, DNS Analytics |
| Zone | Config Rules | Read | Rulesets |
| Zone | Firewall Services | Read | WAF (Pro+ only) |
| Zone | Zone Settings | Read | SSL/TLS Status |
| Account | Workers Scripts | Read | Workers |
| Account | Workers KV Storage | Read | KV Namespaces |
| Account | Workers R2 Storage | Read | R2 Buckets |
| Account | Access: Apps and Policies | Read | Access Applications |
| Account | Cloudflare Tunnel | Read | Tunnels |
| Account | Load Balancing: Monitors and Pools | Read | Load Balancers |
| Account | D1 | Read | D1 Databases |
| Account | Cloudflare Pages | Read | Pages Projects |
| Account | Billing | Read | Workers Daily Limit |

**Tip**: For full monitoring, use Account-level permissions with "All zones" scope.

**Note**: API permission changes may take a few minutes to propagate across Cloudflare's edge. If you still see permission errors after updating your token, wait a few minutes and try again.

**Note**: The `Cloudflare API Usage` check shows which permissions are unused (no resources found), helping you remove unnecessary permissions.

## Installation

### From GitHub Releases
1. Download the MKP file from [Releases](https://github.com/Haxe18/Check_MK-cloudflare/releases)
2. Upload via **Setup → Extension Packages → Upload package**

### Via Command Line
```bash
mkp add cloudflare-1.1.0.mkp
```

## Configuration

1. Go to **Setup → Agents → VM, Cloud, Container → Cloudflare Monitoring**
2. Create a new rule and configure:
   - **API Token**: Your Cloudflare API token
   - **Account ID**: Your Cloudflare Account ID (found in dashboard URL)
   - **Services**: Select which services to monitor
   - **Metrics Cache TTL**: How long to cache metrics (default: 300s, configurable)
   - **Discovery Cache TTL**: How long to cache discovered resources (default: 3600s, configurable)
   - **Timeframe**: Analytics time range (5m, 15m, 1h, 6h, 24h; default: 24h)

   Note: The 5-minute default applies to metrics cache TTL, not to the analytics timeframe.

3. Assign to a host (typically CheckMK server or dedicated monitoring host)
4. Run service discovery

## Services Discovered

After discovery, you'll see services like:
- `Cloudflare Zone example.com` - Zone status
- `Cloudflare Zone Analytics example.com` - HTTP traffic metrics
- `Cloudflare Worker my-worker` - Worker script metrics
- `Cloudflare KV my-namespace` - KV namespace metrics
- `Cloudflare Tunnel my-tunnel` - Tunnel status
- `Cloudflare Pages my-project` - Pages deployment status
- `Cloudflare Pages Functions my-project` - Pages Functions metrics
- `Cloudflare Workers Global` - Workers free tier usage monitoring
- `Cloudflare D1 Global` - D1 free tier usage monitoring (databases, storage, rows)
- `Cloudflare KV Global` - KV free tier usage monitoring (reads, writes, deletes, lists)
- `Cloudflare R2 Global` - R2 storage usage vs included free tier
- `Cloudflare API Usage` - API call counter and errors (incl. `Cloudflare API Errors` graph for active/non-ignored errors)

## Architecture

```
┌───────────────────────────────────────────────────────┐
│ cloudflare Plugin                                     │
│                                                       │
│  WATO Rule → libexec/agent_cloudflare                 │
│      ↓                                                │
│  CloudflareOrchestrator (cached discovery + metrics)  │
│      ├─→ REST API - Resources, Status, Configuration  │
│      └─→ GraphQL API - Analytics, Time-series data    │
│      ↓                                                │
│  <<<cloudflare>>> JSON                                │
│      ↓                                                │
│  agent_based/cloudflare_*.py → Services + Metrics     │
└───────────────────────────────────────────────────────┘
```

## Project Structure

```
cloudflare/
├── lib/                              # Core library (Special Agent)
│   ├── constants.py                  # Centralized constants
│   ├── client.py                     # Cloudflare API client (REST + GraphQL)
│   ├── orchestrator.py               # Service coordination
│   ├── base.py                       # CloudflareSection base class
│   ├── types.py                      # Data types (Resource, MetricResult)
│   ├── cache.py                      # Caching layer (thread-safe)
│   ├── errors.py                     # Error collection (thread-safe)
│   ├── logger.py                     # Logging utilities
│   ├── parallel.py                   # Parallel execution utilities
│   └── services/                     # Service implementations
│       ├── zones.py
│       ├── zone_analytics.py
│       ├── workers.py
│       └── ...
├── libexec/                          # Special agent entrypoint
│   └── agent_cloudflare
├── agent_based/                      # CheckMK check plugins
│   ├── cloudflare.py                 # Parser + API counter
│   ├── cloudflare_zones.py
│   ├── cloudflare_workers.py
│   └── ...
├── rulesets/                         # WATO configuration rules
├── graphing/                         # Metric graph definitions
├── server_side_calls/                # Special agent CLI mapping
└── checkman/                         # Service documentation (incl. *_global and API counter docs)
```

## Testing

```bash
./cloudflare/libexec/agent_cloudflare \
  --api-token "your-api-token" \
  --account-id "your-account-id" \
  --services workers,kv,zones \
  --timeframe 1h
```

## Automation

The repository includes two GitHub Actions for monthly limit maintenance:

- `monthly-limits-check.yml`: runs on the 1st day of each month, refreshes Cloudflare limit constants from docs, and opens/updates a PR if changes are detected.
- `tag-on-merged-limits-pr.yml`: after merging that PR, creates the next patch tag (`vX.Y.Z`) on the merge commit.

The existing release workflow (`release.yml`) already triggers on `v*` tags, so merging a monthly limits PR can automatically create a new release.

## Troubleshooting

### No Services Discovered
- Verify API Token has correct permissions
- Check Account ID is correct
- Ensure at least one service is enabled in the rule

### Performance Metrics Missing (TTFB, Origin Response)
- These metrics require **Pro+ plan** or higher
- Free zones will show 0 for these metrics
- Check `resource.metadata["plan"]` in debug output

### API Errors Showing
- Check `Cloudflare API Usage` service for error details
- Use the dedicated `Cloudflare API Errors` graph to track active (non-ignored) error count over time
- Common issues: Missing permissions, invalid token, rate limiting
- Configure `ignore_error_patterns` in ruleset to suppress known errors

### "Permission denied: subscriptions" Warning
- This occurs when the plugin tries to verify if you have a paid Workers plan.
- **Fix 1 (Recommended)**: Add `Account > Billing > Read` permission to your API Token.
- **Fix 2**: Add `subscriptions` to the "Ignore error patterns" in the WATO rule. The plugin will safely assume the Free plan (100k daily limit).

### GraphQL Errors
- Some metrics may not be available for all account types
- DNS Analytics only supports count metrics (no latency via GraphQL)
- Check Cloudflare API documentation for field availability

### Threshold Configuration
- D1 thresholds (`storage_levels`, `query_count_levels`) use CheckMK SimpleLevels only.
- Global checks (`workers_global`, `kv_global`, `d1_global`, `r2_global`) use `free_tier_monitoring` (bool, default `True`).
- If `free_tier_monitoring=False`, free-tier percentage escalation is disabled, but metrics are still collected and graphed.

### Data Discrepancy vs Cloudflare Dashboard
- **Zone Analytics**: Cloudflare aggregates basic metrics (requests, bandwidth) in 1-hour buckets aligned to the hour. The plugin starts at the hour the timeframe begins in, so the values cover the whole timeframe plus up to one extra hour (for example 1h at 10:15 covers 09:00-10:15).
- **KV and D1**: Per-namespace and per-database values cover exactly the configured timeframe. Daily and monthly usage values follow the calendar day and month (UTC).
- **R2**: Storage and object count are the newest snapshot of the last 24 hours.
- **Zones**: Only zones of the configured account are monitored, even if the token can see more.
- **Tunnels**: Deleted tunnels are not monitored. Status `healthy` is OK, `degraded` and `inactive` (never run) are WARN, `down` is CRIT.
- **Timeframes**: The Dashboard often uses different aggregation windows than the plugin (which defaults to 24h for some views but 5m for rate calculation in CheckMK).

## API Documentation

- [Cloudflare GraphQL Analytics API](https://developers.cloudflare.com/analytics/graphql-api/)
- [Cloudflare REST API](https://developers.cloudflare.com/api/)
- [GraphQL Schema Explorer](https://developers.cloudflare.com/analytics/graphql-api/getting-started/explore-graphql-schema/)
- [Workers Limits](https://developers.cloudflare.com/workers/platform/limits/) / [Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [KV Limits](https://developers.cloudflare.com/kv/platform/limits/) / [Pricing](https://developers.cloudflare.com/kv/platform/pricing/)
- [D1 Limits](https://developers.cloudflare.com/d1/platform/limits/) / [Pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [R2 Limits](https://developers.cloudflare.com/r2/platform/limits/) / [Pricing](https://developers.cloudflare.com/r2/pricing/)

## License

WTFPL (Do What The Fuck You Want To Public License)

## Contributing

Pull requests welcome! Please ensure code follows existing patterns and includes documentation updates.
