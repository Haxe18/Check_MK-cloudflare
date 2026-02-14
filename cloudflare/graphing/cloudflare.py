#!/usr/bin/env python3
"""Graphing definitions for Cloudflare Monitoring.

This module defines metrics, perfometers, and graphs for visualizing
Cloudflare usage data in Checkmk.
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, SINotation, Unit
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

# =============================================================================
# Units
# =============================================================================

UNIT_COUNT = Unit(DecimalNotation(""))
UNIT_BYTES = Unit(SINotation("B"))
UNIT_PERCENTAGE = Unit(DecimalNotation("%"))
UNIT_MS = Unit(DecimalNotation("ms"))

# =============================================================================
# API Counter Metrics
# =============================================================================

metric_cloudflare_api_requests = Metric(
    name="cloudflare_api_requests",
    title=Title("API Requests"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_api_elapsed_time = Metric(
    name="cloudflare_api_elapsed_time",
    title=Title("API Elapsed Time"),
    unit=Unit(DecimalNotation("s")),
    color=Color.GREEN,
)

# =============================================================================
# Workers Metrics
# =============================================================================

metric_cloudflare_worker_requests = Metric(
    name="cloudflare_worker_requests",
    title=Title("Worker Requests"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_worker_requests_today = Metric(
    name="cloudflare_worker_requests_today",
    title=Title("Worker Requests Today"),
    unit=UNIT_COUNT,
    color=Color.DARK_BLUE,
)

metric_cloudflare_worker_errors = Metric(
    name="cloudflare_worker_errors",
    title=Title("Worker Errors"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_worker_error_rate = Metric(
    name="cloudflare_worker_error_rate",
    title=Title("Worker Error Rate"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

metric_cloudflare_worker_cpu_p50 = Metric(
    name="cloudflare_worker_cpu_p50",
    title=Title("Worker CPU Time P50 (Median)"),
    unit=UNIT_MS,
    color=Color.GREEN,
)

metric_cloudflare_worker_cpu_p90 = Metric(
    name="cloudflare_worker_cpu_p90",
    title=Title("Worker CPU Time P90 (90th Percentile)"),
    unit=UNIT_MS,
    color=Color.CYAN,
)

metric_cloudflare_worker_cpu_p99 = Metric(
    name="cloudflare_worker_cpu_p99",
    title=Title("Worker CPU Time P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.DARK_GREEN,
)

metric_cloudflare_worker_cpu_p999 = Metric(
    name="cloudflare_worker_cpu_p999",
    title=Title("Worker CPU Time P999 (99.9th Percentile)"),
    unit=UNIT_MS,
    color=Color.RED,
)

# Wall Time quantiles
metric_cloudflare_worker_wall_p50 = Metric(
    name="cloudflare_worker_wall_p50",
    title=Title("Worker Wall Time P50 (Median)"),
    unit=UNIT_MS,
    color=Color.BLUE,
)

metric_cloudflare_worker_wall_p90 = Metric(
    name="cloudflare_worker_wall_p90",
    title=Title("Worker Wall Time P90 (90th Percentile)"),
    unit=UNIT_MS,
    color=Color.CYAN,
)

metric_cloudflare_worker_wall_p99 = Metric(
    name="cloudflare_worker_wall_p99",
    title=Title("Worker Wall Time P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.DARK_BLUE,
)

metric_cloudflare_worker_wall_p999 = Metric(
    name="cloudflare_worker_wall_p999",
    title=Title("Worker Wall Time P999 (99.9th Percentile)"),
    unit=UNIT_MS,
    color=Color.PURPLE,
)

# Duration quantiles
metric_cloudflare_worker_duration_p50 = Metric(
    name="cloudflare_worker_duration_p50",
    title=Title("Worker Request Duration P50 (Median)"),
    unit=UNIT_MS,
    color=Color.ORANGE,
)

metric_cloudflare_worker_duration_p90 = Metric(
    name="cloudflare_worker_duration_p90",
    title=Title("Worker Request Duration P90 (90th Percentile)"),
    unit=UNIT_MS,
    color=Color.YELLOW,
)

metric_cloudflare_worker_duration_p99 = Metric(
    name="cloudflare_worker_duration_p99",
    title=Title("Worker Request Duration P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.BROWN,
)

metric_cloudflare_worker_duration_p999 = Metric(
    name="cloudflare_worker_duration_p999",
    title=Title("Worker Request Duration P999 (99.9th Percentile)"),
    unit=UNIT_MS,
    color=Color.RED,
)

# Workers Usage (Account-wide)
metric_cloudflare_workers_requests_today = Metric(
    name="cloudflare_workers_requests_today",
    title=Title("Total Requests Today"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_workers_daily_limit = Metric(
    name="cloudflare_workers_daily_limit",
    title=Title("Daily Limit"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_workers_usage_percent = Metric(
    name="cloudflare_workers_usage_percent",
    title=Title("Daily Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

# Workers Monthly (Account-wide)
metric_cloudflare_workers_requests_month = Metric(
    name="cloudflare_workers_requests_month",
    title=Title("Requests This Month"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

# Workers Per-Worker Breakdown (for stacked graph in Global check)
metric_cloudflare_workers_top1_requests = Metric(
    name="cloudflare_workers_top1_requests",
    title=Title("Top Worker #1"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_workers_top2_requests = Metric(
    name="cloudflare_workers_top2_requests",
    title=Title("Top Worker #2"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_workers_top3_requests = Metric(
    name="cloudflare_workers_top3_requests",
    title=Title("Top Worker #3"),
    unit=UNIT_COUNT,
    color=Color.CYAN,
)

metric_cloudflare_workers_top4_requests = Metric(
    name="cloudflare_workers_top4_requests",
    title=Title("Top Worker #4"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_cloudflare_workers_top5_requests = Metric(
    name="cloudflare_workers_top5_requests",
    title=Title("Top Worker #5"),
    unit=UNIT_COUNT,
    color=Color.PURPLE,
)

metric_cloudflare_workers_other_requests = Metric(
    name="cloudflare_workers_other_requests",
    title=Title("Other Workers"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

# =============================================================================
# KV Metrics
# =============================================================================

metric_cloudflare_kv_reads = Metric(
    name="cloudflare_kv_reads",
    title=Title("KV Reads"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_kv_writes = Metric(
    name="cloudflare_kv_writes",
    title=Title("KV Writes"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_kv_deletes = Metric(
    name="cloudflare_kv_deletes",
    title=Title("KV Deletes"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_kv_lists = Metric(
    name="cloudflare_kv_lists",
    title=Title("KV Lists"),
    unit=UNIT_COUNT,
    color=Color.YELLOW,
)

metric_cloudflare_kv_keys = Metric(
    name="cloudflare_kv_keys",
    title=Title("KV Keys"),
    unit=UNIT_COUNT,
    color=Color.DARK_BLUE,
)

metric_cloudflare_kv_storage = Metric(
    name="cloudflare_kv_storage",
    title=Title("KV Storage"),
    unit=UNIT_BYTES,  # Auto-converts to KB/MB/GB
    color=Color.PURPLE,
)

# KV Latency Metrics (matching Cloudflare dashboard: P50, P75, P90, P99)
metric_cloudflare_kv_latency_p50 = Metric(
    name="cloudflare_kv_latency_p50",
    title=Title("KV Latency P50 (Median)"),
    unit=UNIT_MS,
    color=Color.GREEN,
)

metric_cloudflare_kv_latency_p75 = Metric(
    name="cloudflare_kv_latency_p75",
    title=Title("KV Latency P75 (75th Percentile)"),
    unit=UNIT_MS,
    color=Color.CYAN,
)

metric_cloudflare_kv_latency_p90 = Metric(
    name="cloudflare_kv_latency_p90",
    title=Title("KV Latency P90 (90th Percentile)"),
    unit=UNIT_MS,
    color=Color.YELLOW,
)

metric_cloudflare_kv_latency_p99 = Metric(
    name="cloudflare_kv_latency_p99",
    title=Title("KV Latency P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.ORANGE,
)

# KV Read Status Metrics (hot/cold/not_found)
metric_cloudflare_kv_hot_reads = Metric(
    name="cloudflare_kv_hot_reads",
    title=Title("KV Hot Reads"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_kv_cold_reads = Metric(
    name="cloudflare_kv_cold_reads",
    title=Title("KV Cold Reads"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_kv_not_found = Metric(
    name="cloudflare_kv_not_found",
    title=Title("KV Not Found"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

# KV Monthly Summary Metrics
metric_cloudflare_kv_reads_month = Metric(
    name="cloudflare_kv_reads_month",
    title=Title("KV Reads (Month)"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_kv_writes_month = Metric(
    name="cloudflare_kv_writes_month",
    title=Title("KV Writes (Month)"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_kv_lists_month = Metric(
    name="cloudflare_kv_lists_month",
    title=Title("KV Lists (Month)"),
    unit=UNIT_COUNT,
    color=Color.YELLOW,
)

metric_cloudflare_kv_deletes_month = Metric(
    name="cloudflare_kv_deletes_month",
    title=Title("KV Deletes (Month)"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

# =============================================================================
# Zone Analytics Metrics
# =============================================================================

metric_cloudflare_zone_requests = Metric(
    name="cloudflare_zone_requests",
    title=Title("Zone Requests"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_zone_bandwidth = Metric(
    name="cloudflare_zone_bandwidth",
    title=Title("Zone Bandwidth"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

metric_cloudflare_zone_threats = Metric(
    name="cloudflare_zone_threats",
    title=Title("Threats Blocked"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_zone_page_views = Metric(
    name="cloudflare_zone_page_views",
    title=Title("Page Views"),
    unit=UNIT_COUNT,
    color=Color.CYAN,
)

metric_cloudflare_zone_cached_requests = Metric(
    name="cloudflare_zone_cached_requests",
    title=Title("Cached Requests"),
    unit=UNIT_COUNT,
    color=Color.DARK_BLUE,
)

metric_cloudflare_zone_cache_hit_ratio = Metric(
    name="cloudflare_zone_cache_hit_ratio",
    title=Title("Cache Hit Ratio"),
    unit=UNIT_PERCENTAGE,
    color=Color.DARK_GREEN,
)

# Zone Analytics Performance Metrics (Pro+ plans)
# Time to First Byte (TTFB)
metric_cloudflare_zone_ttfb_p50 = Metric(
    name="cloudflare_zone_ttfb_p50",
    title=Title("TTFB P50 (Median)"),
    unit=UNIT_MS,
    color=Color.BLUE,
)

metric_cloudflare_zone_ttfb_p95 = Metric(
    name="cloudflare_zone_ttfb_p95",
    title=Title("TTFB P95 (95th Percentile)"),
    unit=UNIT_MS,
    color=Color.CYAN,
)

metric_cloudflare_zone_ttfb_p99 = Metric(
    name="cloudflare_zone_ttfb_p99",
    title=Title("TTFB P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.DARK_BLUE,
)

# Origin Response Duration
metric_cloudflare_zone_origin_p50 = Metric(
    name="cloudflare_zone_origin_p50",
    title=Title("Origin Response P50 (Median)"),
    unit=UNIT_MS,
    color=Color.GREEN,
)

metric_cloudflare_zone_origin_p95 = Metric(
    name="cloudflare_zone_origin_p95",
    title=Title("Origin Response P95 (95th Percentile)"),
    unit=UNIT_MS,
    color=Color.YELLOW,
)

metric_cloudflare_zone_origin_p99 = Metric(
    name="cloudflare_zone_origin_p99",
    title=Title("Origin Response P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.DARK_GREEN,
)

# Edge DNS Response Time
metric_cloudflare_zone_edge_dns_p50 = Metric(
    name="cloudflare_zone_edge_dns_p50",
    title=Title("Edge DNS P50 (Median)"),
    unit=UNIT_MS,
    color=Color.ORANGE,
)

metric_cloudflare_zone_edge_dns_p95 = Metric(
    name="cloudflare_zone_edge_dns_p95",
    title=Title("Edge DNS P95 (95th Percentile)"),
    unit=UNIT_MS,
    color=Color.BROWN,
)

metric_cloudflare_zone_edge_dns_p99 = Metric(
    name="cloudflare_zone_edge_dns_p99",
    title=Title("Edge DNS P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.RED,
)

# =============================================================================
# DNS Analytics Metrics
# =============================================================================

metric_cloudflare_dns_query_count = Metric(
    name="cloudflare_dns_query_count",
    title=Title("DNS Query Count"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_dns_response_time = Metric(
    name="cloudflare_dns_response_time",
    title=Title("DNS Response Time"),
    unit=UNIT_MS,
    color=Color.GREEN,
)

metric_cloudflare_dns_noerror = Metric(
    name="cloudflare_dns_noerror",
    title=Title("DNS NOERROR"),
    unit=UNIT_COUNT,
    color=Color.DARK_GREEN,
)

metric_cloudflare_dns_nxdomain = Metric(
    name="cloudflare_dns_nxdomain",
    title=Title("DNS NXDOMAIN"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_cloudflare_dns_servfail = Metric(
    name="cloudflare_dns_servfail",
    title=Title("DNS SERVFAIL"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

# DNS Response Time Percentiles
metric_cloudflare_dns_response_p50 = Metric(
    name="cloudflare_dns_response_p50",
    title=Title("DNS Response P50 (Median)"),
    unit=UNIT_MS,
    color=Color.GREEN,
)

metric_cloudflare_dns_response_p95 = Metric(
    name="cloudflare_dns_response_p95",
    title=Title("DNS Response P95 (95th Percentile)"),
    unit=UNIT_MS,
    color=Color.YELLOW,
)

metric_cloudflare_dns_response_p99 = Metric(
    name="cloudflare_dns_response_p99",
    title=Title("DNS Response P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.RED,
)

# =============================================================================
# WAF Metrics
# =============================================================================

metric_cloudflare_waf_total_events = Metric(
    name="cloudflare_waf_total_events",
    title=Title("WAF Total Events"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_waf_blocked = Metric(
    name="cloudflare_waf_blocked",
    title=Title("WAF Blocked"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_waf_challenged = Metric(
    name="cloudflare_waf_challenged",
    title=Title("WAF Challenged"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

# =============================================================================
# Rulesets Metrics
# =============================================================================

metric_cloudflare_rulesets_total = Metric(
    name="cloudflare_rulesets_total",
    title=Title("Rulesets Total"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_rulesets_redirect = Metric(
    name="cloudflare_rulesets_redirect",
    title=Title("Redirect Rules"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_rulesets_cache = Metric(
    name="cloudflare_rulesets_cache",
    title=Title("Cache Rules"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_cloudflare_rulesets_config = Metric(
    name="cloudflare_rulesets_config",
    title=Title("Config Rules"),
    unit=UNIT_COUNT,
    color=Color.PURPLE,
)

metric_cloudflare_rulesets_origin = Metric(
    name="cloudflare_rulesets_origin",
    title=Title("Origin Rules"),
    unit=UNIT_COUNT,
    color=Color.CYAN,
)

# =============================================================================
# Access Metrics
# =============================================================================

metric_cloudflare_access_policies = Metric(
    name="cloudflare_access_policies",
    title=Title("Access Policies"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_access_idps = Metric(
    name="cloudflare_access_idps",
    title=Title("Access IDPs"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

# =============================================================================
# Tunnel Metrics
# =============================================================================

metric_cloudflare_tunnel_status = Metric(
    name="cloudflare_tunnel_status",
    title=Title("Tunnel Status"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_tunnel_connections = Metric(
    name="cloudflare_tunnel_connections",
    title=Title("Tunnel Connections"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

# =============================================================================
# Load Balancer Metrics
# =============================================================================

metric_cloudflare_lb_healthy = Metric(
    name="cloudflare_lb_healthy",
    title=Title("Pool Healthy"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_lb_origin_count = Metric(
    name="cloudflare_lb_origin_count",
    title=Title("Origin Count"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_lb_healthy_origins = Metric(
    name="cloudflare_lb_healthy_origins",
    title=Title("Healthy Origins"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_lb_healthy_ratio = Metric(
    name="cloudflare_lb_healthy_ratio",
    title=Title("Healthy Origin Ratio"),
    unit=UNIT_PERCENTAGE,
    color=Color.DARK_GREEN,
)

metric_cloudflare_lb_rtt = Metric(
    name="cloudflare_lb_rtt",
    title=Title("Health Check RTT"),
    unit=UNIT_MS,
    color=Color.BLUE,
)

# =============================================================================
# Perfometers
# =============================================================================

perfometer_cloudflare_worker_error_rate = Perfometer(
    name="cloudflare_worker_error_rate",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["cloudflare_worker_error_rate"],
)

perfometer_cloudflare_zone_cache_hit_ratio = Perfometer(
    name="cloudflare_zone_cache_hit_ratio",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["cloudflare_zone_cache_hit_ratio"],
)

perfometer_cloudflare_lb_healthy_ratio = Perfometer(
    name="cloudflare_lb_healthy_ratio",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["cloudflare_lb_healthy_ratio"],
)

# =============================================================================
# Graphs
# =============================================================================

# API Counter
graph_cloudflare_api = Graph(
    name="cloudflare_api",
    title=Title("Cloudflare API Usage"),
    compound_lines=["cloudflare_api_requests"],
)

# Workers (per-worker)
graph_cloudflare_worker_requests = Graph(
    name="cloudflare_worker_requests",
    title=Title("Worker Requests"),
    compound_lines=["cloudflare_worker_requests"],
    simple_lines=["cloudflare_worker_errors"],
)

graph_cloudflare_worker_requests_today = Graph(
    name="cloudflare_worker_requests_today",
    title=Title("Worker Requests Today"),
    compound_lines=["cloudflare_worker_requests_today"],
)

graph_cloudflare_worker_cpu = Graph(
    name="cloudflare_worker_cpu",
    title=Title("Worker CPU Time"),
    compound_lines=["cloudflare_worker_cpu_p50"],
    simple_lines=[
        "cloudflare_worker_cpu_p90",
        "cloudflare_worker_cpu_p99",
        "cloudflare_worker_cpu_p999",
    ],
)

graph_cloudflare_worker_wall_time = Graph(
    name="cloudflare_worker_wall_time",
    title=Title("Worker Wall Time"),
    compound_lines=["cloudflare_worker_wall_p50"],
    simple_lines=[
        "cloudflare_worker_wall_p90",
        "cloudflare_worker_wall_p99",
        "cloudflare_worker_wall_p999",
    ],
)

graph_cloudflare_worker_duration = Graph(
    name="cloudflare_worker_duration",
    title=Title("Worker Request Duration"),
    compound_lines=["cloudflare_worker_duration_p50"],
    simple_lines=[
        "cloudflare_worker_duration_p90",
        "cloudflare_worker_duration_p99",
        "cloudflare_worker_duration_p999",
    ],
)

# Workers Usage (account-wide)
graph_cloudflare_workers_usage = Graph(
    name="cloudflare_workers_usage",
    title=Title("Workers Daily Usage"),
    compound_lines=["cloudflare_workers_requests_today"],
    simple_lines=["cloudflare_workers_daily_limit"],
)

# Workers Monthly (account-wide)
graph_cloudflare_workers_monthly = Graph(
    name="cloudflare_workers_monthly",
    title=Title("Workers Monthly Requests"),
    compound_lines=["cloudflare_workers_requests_month"],
)

# Workers Breakdown Stacked Graph (account-wide, shows Top 5 workers + Other)
graph_cloudflare_workers_breakdown = Graph(
    name="cloudflare_workers_breakdown",
    title=Title("Workers Daily Requests by Worker"),
    compound_lines=[
        "cloudflare_workers_other_requests",
        "cloudflare_workers_top5_requests",
        "cloudflare_workers_top4_requests",
        "cloudflare_workers_top3_requests",
        "cloudflare_workers_top2_requests",
        "cloudflare_workers_top1_requests",
    ],
)

# KV
graph_cloudflare_kv_operations = Graph(
    name="cloudflare_kv_operations",
    title=Title("KV Operations"),
    compound_lines=["cloudflare_kv_reads"],
    simple_lines=["cloudflare_kv_writes", "cloudflare_kv_deletes", "cloudflare_kv_lists"],
)

graph_cloudflare_kv_keys = Graph(
    name="cloudflare_kv_keys",
    title=Title("KV Key Count"),
    compound_lines=["cloudflare_kv_keys"],
)

graph_cloudflare_kv_storage = Graph(
    name="cloudflare_kv_storage",
    title=Title("KV Storage"),
    compound_lines=["cloudflare_kv_storage"],
)

graph_cloudflare_kv_latency = Graph(
    name="cloudflare_kv_latency",
    title=Title("KV Operation Latency"),
    compound_lines=["cloudflare_kv_latency_p50"],
    simple_lines=[
        "cloudflare_kv_latency_p75",
        "cloudflare_kv_latency_p90",
        "cloudflare_kv_latency_p99",
    ],
)

graph_cloudflare_kv_read_status = Graph(
    name="cloudflare_kv_read_status",
    title=Title("KV Read Status"),
    compound_lines=["cloudflare_kv_hot_reads"],
    simple_lines=["cloudflare_kv_cold_reads", "cloudflare_kv_not_found"],
)

graph_cloudflare_kv_monthly = Graph(
    name="cloudflare_kv_monthly",
    title=Title("KV Monthly Operations"),
    compound_lines=["cloudflare_kv_reads_month"],
    simple_lines=[
        "cloudflare_kv_writes_month",
        "cloudflare_kv_lists_month",
        "cloudflare_kv_deletes_month",
    ],
)

# =============================================================================
# KV Global Metrics
# =============================================================================

metric_cloudflare_kv_total_namespaces = Metric(
    name="cloudflare_kv_total_namespaces",
    title=Title("KV Total Namespaces"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_kv_daily_reads = Metric(
    name="cloudflare_kv_daily_reads",
    title=Title("KV Daily Reads"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_kv_reads_limit = Metric(
    name="cloudflare_kv_reads_limit",
    title=Title("KV Reads Limit"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_kv_reads_usage_percent = Metric(
    name="cloudflare_kv_reads_usage_percent",
    title=Title("KV Reads Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

metric_cloudflare_kv_daily_writes = Metric(
    name="cloudflare_kv_daily_writes",
    title=Title("KV Daily Writes"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_cloudflare_kv_writes_limit = Metric(
    name="cloudflare_kv_writes_limit",
    title=Title("KV Writes Limit"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_kv_writes_usage_percent = Metric(
    name="cloudflare_kv_writes_usage_percent",
    title=Title("KV Writes Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

metric_cloudflare_kv_daily_deletes = Metric(
    name="cloudflare_kv_daily_deletes",
    title=Title("KV Daily Deletes"),
    unit=UNIT_COUNT,
    color=Color.PURPLE,
)

metric_cloudflare_kv_deletes_limit = Metric(
    name="cloudflare_kv_deletes_limit",
    title=Title("KV Deletes Limit"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_kv_deletes_usage_percent = Metric(
    name="cloudflare_kv_deletes_usage_percent",
    title=Title("KV Deletes Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.PURPLE,
)

metric_cloudflare_kv_daily_lists = Metric(
    name="cloudflare_kv_daily_lists",
    title=Title("KV Daily Lists"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_kv_lists_limit = Metric(
    name="cloudflare_kv_lists_limit",
    title=Title("KV Lists Limit"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_kv_lists_usage_percent = Metric(
    name="cloudflare_kv_lists_usage_percent",
    title=Title("KV Lists Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.GREEN,
)

# =============================================================================
# KV Global Graphs
# =============================================================================

graph_cloudflare_kv_daily_reads = Graph(
    name="cloudflare_kv_daily_reads",
    title=Title("KV Daily Reads vs Limit"),
    compound_lines=["cloudflare_kv_daily_reads"],
    simple_lines=["cloudflare_kv_reads_limit"],
)

graph_cloudflare_kv_daily_writes = Graph(
    name="cloudflare_kv_daily_writes",
    title=Title("KV Daily Writes vs Limit"),
    compound_lines=["cloudflare_kv_daily_writes"],
    simple_lines=["cloudflare_kv_writes_limit"],
)

graph_cloudflare_kv_usage_percent = Graph(
    name="cloudflare_kv_usage_percent",
    title=Title("KV Usage Percentages"),
    compound_lines=["cloudflare_kv_reads_usage_percent"],
    simple_lines=[
        "cloudflare_kv_writes_usage_percent",
        "cloudflare_kv_deletes_usage_percent",
        "cloudflare_kv_lists_usage_percent",
    ],
)

# Zone Analytics
graph_cloudflare_zone_requests = Graph(
    name="cloudflare_zone_requests",
    title=Title("Cloudflare Zone Requests"),
    compound_lines=["cloudflare_zone_requests"],
    simple_lines=["cloudflare_zone_cached_requests"],
)

graph_cloudflare_zone_bandwidth = Graph(
    name="cloudflare_zone_bandwidth",
    title=Title("Cloudflare Zone Bandwidth"),
    compound_lines=["cloudflare_zone_bandwidth"],
)

graph_cloudflare_zone_security = Graph(
    name="cloudflare_zone_security",
    title=Title("Cloudflare Zone Security"),
    compound_lines=["cloudflare_zone_threats"],
)

# Zone Analytics Performance (Pro+ plans)
graph_cloudflare_zone_ttfb = Graph(
    name="cloudflare_zone_ttfb",
    title=Title("Zone Time to First Byte"),
    compound_lines=["cloudflare_zone_ttfb_p50"],
    simple_lines=["cloudflare_zone_ttfb_p95", "cloudflare_zone_ttfb_p99"],
)

graph_cloudflare_zone_origin_response = Graph(
    name="cloudflare_zone_origin_response",
    title=Title("Zone Origin Response Time"),
    compound_lines=["cloudflare_zone_origin_p50"],
    simple_lines=["cloudflare_zone_origin_p95", "cloudflare_zone_origin_p99"],
)

graph_cloudflare_zone_edge_dns = Graph(
    name="cloudflare_zone_edge_dns",
    title=Title("Zone Edge DNS Response Time"),
    compound_lines=["cloudflare_zone_edge_dns_p50"],
    simple_lines=["cloudflare_zone_edge_dns_p95", "cloudflare_zone_edge_dns_p99"],
)

# DNS Analytics
graph_cloudflare_dns_queries = Graph(
    name="cloudflare_dns_queries",
    title=Title("Cloudflare DNS Queries"),
    compound_lines=["cloudflare_dns_query_count"],
)

graph_cloudflare_dns_response = Graph(
    name="cloudflare_dns_response",
    title=Title("Cloudflare DNS Response Time"),
    compound_lines=["cloudflare_dns_response_time"],
)

graph_cloudflare_dns_codes = Graph(
    name="cloudflare_dns_codes",
    title=Title("Cloudflare DNS Response Codes"),
    compound_lines=["cloudflare_dns_noerror"],
    simple_lines=["cloudflare_dns_nxdomain", "cloudflare_dns_servfail"],
)

graph_cloudflare_dns_response_percentiles = Graph(
    name="cloudflare_dns_response_percentiles",
    title=Title("Cloudflare DNS Response Time Percentiles"),
    compound_lines=["cloudflare_dns_response_p50"],
    simple_lines=["cloudflare_dns_response_p95", "cloudflare_dns_response_p99"],
)

# WAF
graph_cloudflare_waf = Graph(
    name="cloudflare_waf",
    title=Title("Cloudflare WAF Events"),
    compound_lines=["cloudflare_waf_total_events"],
    simple_lines=["cloudflare_waf_blocked", "cloudflare_waf_challenged"],
)

# Rulesets
graph_cloudflare_rulesets = Graph(
    name="cloudflare_rulesets",
    title=Title("Cloudflare Rulesets"),
    compound_lines=["cloudflare_rulesets_total"],
    simple_lines=[
        "cloudflare_rulesets_redirect",
        "cloudflare_rulesets_cache",
        "cloudflare_rulesets_config",
        "cloudflare_rulesets_origin",
    ],
)

# Access
graph_cloudflare_access = Graph(
    name="cloudflare_access",
    title=Title("Cloudflare Access"),
    compound_lines=["cloudflare_access_policies"],
    simple_lines=["cloudflare_access_idps"],
)

# Tunnel
graph_cloudflare_tunnel = Graph(
    name="cloudflare_tunnel",
    title=Title("Cloudflare Tunnel"),
    compound_lines=["cloudflare_tunnel_connections"],
)

# Load Balancer
graph_cloudflare_lb_origins = Graph(
    name="cloudflare_lb_origins",
    title=Title("Cloudflare Load Balancer Origins"),
    compound_lines=["cloudflare_lb_origin_count"],
    simple_lines=["cloudflare_lb_healthy_origins"],
)

graph_cloudflare_lb_rtt = Graph(
    name="cloudflare_lb_rtt",
    title=Title("Cloudflare Load Balancer Health Check RTT"),
    compound_lines=["cloudflare_lb_rtt"],
)

# =============================================================================
# R2 Metrics
# =============================================================================

metric_cloudflare_r2_storage = Metric(
    name="cloudflare_r2_storage",
    title=Title("R2 Storage"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_cloudflare_r2_objects = Metric(
    name="cloudflare_r2_objects",
    title=Title("R2 Object Count"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

# =============================================================================
# Pages Metrics
# =============================================================================

UNIT_SECONDS = Unit(DecimalNotation("s"))

metric_cloudflare_pages_deployment_status = Metric(
    name="cloudflare_pages_deployment_status",
    title=Title("Deployment Status"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_pages_deployment_age = Metric(
    name="cloudflare_pages_deployment_age",
    title=Title("Deployment Age"),
    unit=UNIT_SECONDS,
    color=Color.GREEN,
)

metric_cloudflare_pages_domains_count = Metric(
    name="cloudflare_pages_domains_count",
    title=Title("Custom Domains"),
    unit=UNIT_COUNT,
    color=Color.CYAN,
)

# Pages Functions Metrics
metric_cloudflare_pages_functions_invocations = Metric(
    name="cloudflare_pages_functions_invocations",
    title=Title("Functions Invocations"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_pages_functions_errors = Metric(
    name="cloudflare_pages_functions_errors",
    title=Title("Functions Errors"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_pages_functions_error_rate = Metric(
    name="cloudflare_pages_functions_error_rate",
    title=Title("Functions Error Rate"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

metric_cloudflare_pages_functions_cpu_p50 = Metric(
    name="cloudflare_pages_functions_cpu_p50",
    title=Title("Functions CPU Time P50 (Median)"),
    unit=UNIT_MS,
    color=Color.GREEN,
)

metric_cloudflare_pages_functions_cpu_p99 = Metric(
    name="cloudflare_pages_functions_cpu_p99",
    title=Title("Functions CPU Time P99 (99th Percentile)"),
    unit=UNIT_MS,
    color=Color.DARK_GREEN,
)

# Pages Perfometers
perfometer_cloudflare_pages_functions_error_rate = Perfometer(
    name="cloudflare_pages_functions_error_rate",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["cloudflare_pages_functions_error_rate"],
)

# Pages Graphs
graph_cloudflare_pages_functions_requests = Graph(
    name="cloudflare_pages_functions_requests",
    title=Title("Pages Functions Invocations"),
    compound_lines=["cloudflare_pages_functions_invocations"],
    simple_lines=["cloudflare_pages_functions_errors"],
)

graph_cloudflare_pages_functions_cpu = Graph(
    name="cloudflare_pages_functions_cpu",
    title=Title("Pages Functions CPU Time"),
    compound_lines=["cloudflare_pages_functions_cpu_p50"],
    simple_lines=["cloudflare_pages_functions_cpu_p99"],
)

# R2 Graphs
graph_cloudflare_r2_storage = Graph(
    name="cloudflare_r2_storage",
    title=Title("R2 Storage Usage"),
    compound_lines=["cloudflare_r2_storage"],
)

graph_cloudflare_r2_objects = Graph(
    name="cloudflare_r2_objects",
    title=Title("R2 Object Count"),
    compound_lines=["cloudflare_r2_objects"],
)

# =============================================================================
# R2 Global Metrics
# =============================================================================

metric_cloudflare_r2_total_buckets = Metric(
    name="cloudflare_r2_total_buckets",
    title=Title("R2 Total Buckets"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_r2_total_objects = Metric(
    name="cloudflare_r2_total_objects",
    title=Title("R2 Total Objects"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_r2_total_storage = Metric(
    name="cloudflare_r2_total_storage",
    title=Title("R2 Total Storage"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_cloudflare_r2_max_storage = Metric(
    name="cloudflare_r2_max_storage",
    title=Title("R2 Included Free Tier"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)

metric_cloudflare_r2_storage_usage_percent = Metric(
    name="cloudflare_r2_storage_usage_percent",
    title=Title("R2 Storage Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

# =============================================================================
# R2 Global Graphs
# =============================================================================

graph_cloudflare_r2_global_storage = Graph(
    name="cloudflare_r2_global_storage",
    title=Title("R2 Total Storage vs Included Free Tier"),
    compound_lines=["cloudflare_r2_total_storage"],
    simple_lines=["cloudflare_r2_max_storage"],
)

graph_cloudflare_r2_usage_percent = Graph(
    name="cloudflare_r2_usage_percent",
    title=Title("R2 Storage Usage Percentage"),
    compound_lines=["cloudflare_r2_storage_usage_percent"],
)

# =============================================================================
# D1 Metrics
# =============================================================================

metric_cloudflare_d1_status = Metric(
    name="cloudflare_d1_status",
    title=Title("D1 Status"),
    unit=UNIT_COUNT,
    color=Color.GRAY,
)

metric_cloudflare_d1_storage = Metric(
    name="cloudflare_d1_storage",
    title=Title("D1 Storage Size"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_cloudflare_d1_queries = Metric(
    name="cloudflare_d1_queries",
    title=Title("D1 Queries"),
    unit=UNIT_COUNT,
    color=Color.GREEN,
)

metric_cloudflare_d1_rows_read = Metric(
    name="cloudflare_d1_rows_read",
    title=Title("D1 Rows Read"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_d1_rows_written = Metric(
    name="cloudflare_d1_rows_written",
    title=Title("D1 Rows Written"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_cloudflare_d1_duration_avg = Metric(
    name="cloudflare_d1_duration_avg",
    title=Title("D1 Avg Query Duration"),
    unit=UNIT_MS,
    color=Color.PURPLE,
)

# =============================================================================
# D1 Graphs
# =============================================================================

graph_cloudflare_d1_storage = Graph(
    name="cloudflare_d1_storage",
    title=Title("D1 Database Storage"),
    compound_lines=["cloudflare_d1_storage"],
)

graph_cloudflare_d1_throughput = Graph(
    name="cloudflare_d1_throughput",
    title=Title("D1 Database Throughput"),
    compound_lines=["cloudflare_d1_queries"],
)

graph_cloudflare_d1_rows = Graph(
    name="cloudflare_d1_rows",
    title=Title("D1 Database Rows"),
    compound_lines=["cloudflare_d1_rows_read"],
    simple_lines=["cloudflare_d1_rows_written"],
)

graph_cloudflare_d1_duration = Graph(
    name="cloudflare_d1_duration",
    title=Title("D1 Database Performance"),
    compound_lines=["cloudflare_d1_duration_avg"],
)

# =============================================================================
# D1 Global Metrics
# =============================================================================

metric_cloudflare_d1_total_databases = Metric(
    name="cloudflare_d1_total_databases",
    title=Title("D1 Total Databases"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_d1_max_databases = Metric(
    name="cloudflare_d1_max_databases",
    title=Title("D1 Max Databases (Limit)"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_d1_total_storage = Metric(
    name="cloudflare_d1_total_storage",
    title=Title("D1 Total Storage"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

metric_cloudflare_d1_max_storage = Metric(
    name="cloudflare_d1_max_storage",
    title=Title("D1 Max Storage (Limit)"),
    unit=UNIT_BYTES,
    color=Color.RED,
)

metric_cloudflare_d1_storage_usage_percent = Metric(
    name="cloudflare_d1_storage_usage_percent",
    title=Title("D1 Storage Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)

metric_cloudflare_d1_daily_rows_read = Metric(
    name="cloudflare_d1_daily_rows_read",
    title=Title("D1 Daily Rows Read"),
    unit=UNIT_COUNT,
    color=Color.BLUE,
)

metric_cloudflare_d1_daily_rows_read_limit = Metric(
    name="cloudflare_d1_daily_rows_read_limit",
    title=Title("D1 Daily Rows Read (Limit)"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_d1_rows_read_usage_percent = Metric(
    name="cloudflare_d1_rows_read_usage_percent",
    title=Title("D1 Rows Read Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.GREEN,
)

metric_cloudflare_d1_daily_rows_written = Metric(
    name="cloudflare_d1_daily_rows_written",
    title=Title("D1 Daily Rows Written"),
    unit=UNIT_COUNT,
    color=Color.ORANGE,
)

metric_cloudflare_d1_daily_rows_written_limit = Metric(
    name="cloudflare_d1_daily_rows_written_limit",
    title=Title("D1 Daily Rows Written (Limit)"),
    unit=UNIT_COUNT,
    color=Color.RED,
)

metric_cloudflare_d1_rows_written_usage_percent = Metric(
    name="cloudflare_d1_rows_written_usage_percent",
    title=Title("D1 Rows Written Usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

# =============================================================================
# D1 Global Graphs
# =============================================================================

graph_cloudflare_d1_databases = Graph(
    name="cloudflare_d1_databases",
    title=Title("D1 Databases"),
    compound_lines=["cloudflare_d1_total_databases"],
    simple_lines=["cloudflare_d1_max_databases"],
)

graph_cloudflare_d1_global_storage = Graph(
    name="cloudflare_d1_global_storage",
    title=Title("D1 Total Storage vs Limit"),
    compound_lines=["cloudflare_d1_total_storage"],
    simple_lines=["cloudflare_d1_max_storage"],
)

graph_cloudflare_d1_daily_rows_read = Graph(
    name="cloudflare_d1_daily_rows_read",
    title=Title("D1 Daily Rows Read vs Limit"),
    compound_lines=["cloudflare_d1_daily_rows_read"],
    simple_lines=["cloudflare_d1_daily_rows_read_limit"],
)

graph_cloudflare_d1_daily_rows_written = Graph(
    name="cloudflare_d1_daily_rows_written",
    title=Title("D1 Daily Rows Written vs Limit"),
    compound_lines=["cloudflare_d1_daily_rows_written"],
    simple_lines=["cloudflare_d1_daily_rows_written_limit"],
)

graph_cloudflare_d1_usage_percent = Graph(
    name="cloudflare_d1_usage_percent",
    title=Title("D1 Usage Percentages"),
    compound_lines=["cloudflare_d1_storage_usage_percent"],
    simple_lines=[
        "cloudflare_d1_rows_read_usage_percent",
        "cloudflare_d1_rows_written_usage_percent",
    ],
)
