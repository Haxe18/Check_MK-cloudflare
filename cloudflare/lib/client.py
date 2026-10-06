#!/usr/bin/env python3
"""Cloudflare API client for REST and GraphQL endpoints."""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .cache import APICounter
from .constants import (
    CLOUDFLARE_API_BASE_URL,
    CLOUDFLARE_ERROR_CODE_UNAUTHORIZED,
    CLOUDFLARE_GRAPHQL_URL,
    CLOUDFLARE_PERMISSION_ERROR_CODES,
    D1_FREE_DAILY_ROWS_READ,
    D1_FREE_DAILY_ROWS_WRITTEN,
    D1_FREE_MAX_DATABASES,
    D1_FREE_MAX_STORAGE,
    D1_PAID_MAX_DATABASES,
    D1_PAID_MAX_STORAGE,
    D1_PAID_MONTHLY_ROWS_READ,
    D1_PAID_MONTHLY_ROWS_WRITTEN,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT,
    ENDPOINT_TYPE_GRAPHQL,
    ERROR_CATEGORY_API,
    ERROR_SERVICE_GRAPHQL,
    ERROR_SERVICE_REST,
    FREE_PLAN_DAILY_LIMIT,
    KV_FREE_DAILY_DELETES,
    KV_FREE_DAILY_LISTS,
    KV_FREE_DAILY_READS,
    KV_FREE_DAILY_WRITES,
    KV_FREE_MAX_STORAGE,
    KV_PAID_MAX_STORAGE,
    KV_PAID_MONTHLY_DELETES,
    KV_PAID_MONTHLY_LISTS,
    KV_PAID_MONTHLY_READS,
    KV_PAID_MONTHLY_WRITES,
    R2_FREE_STORAGE,
    R2_JURISDICTIONS,
    TIMEFRAME_24H,
    TIMEFRAME_MINUTES,
)
from .errors import ErrorCollector
from .logger import LoggerMixin
from .parallel import parallel_map


def _weighted_avg(values: list[tuple[float, int]], to_ms: bool = False) -> float:
    """Calculate weighted average.

    Args:
        values: List of (value, weight) tuples
        to_ms: If True, convert from microseconds to milliseconds

    Returns:
        Weighted average or 0.0 if empty/no weight
    """
    if not values:
        return 0.0
    total_weight = sum(w for _, w in values)
    if total_weight == 0:
        return 0.0
    result = sum(v * w for v, w in values) / total_weight
    return result / 1000 if to_ms else result


class CloudflareClient(LoggerMixin):
    """Wrapper for Cloudflare API (REST + GraphQL)."""

    BASE_URL = CLOUDFLARE_API_BASE_URL
    GRAPHQL_URL = CLOUDFLARE_GRAPHQL_URL

    def __init__(
        self,
        api_token: str,
        account_id: str,
        api_counter: APICounter | None = None,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Initialize Cloudflare client.

        Args:
            api_token: Cloudflare API token
            account_id: Cloudflare account ID
            api_counter: Optional API counter for tracking requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_token = api_token
        self.account_id = account_id
        self.api_counter = api_counter or APICounter()
        self.timeout = timeout
        self.max_retries = max_retries
        self.error_collector = ErrorCollector()  # Collect errors for reporting to Check_MK

        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _get_time_range(timeframe: str) -> tuple[str, str]:
        """Calculate time range based on timeframe.

        Args:
            timeframe: Timeframe string (5m, 15m, 1h, 6h, 24h)

        Returns:
            Tuple of (start_datetime, end_datetime) in ISO format
        """
        minutes = TIMEFRAME_MINUTES.get(timeframe, 1440)
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=minutes)

        return (
            start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @staticmethod
    def _get_date_range(timeframe: str) -> tuple[str, str]:
        """Calculate date range based on timeframe.

        Args:
            timeframe: Timeframe string

        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        minutes = TIMEFRAME_MINUTES.get(timeframe, 1440)
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=minutes)

        return (
            start.strftime("%Y-%m-%d"),
            now.strftime("%Y-%m-%d"),
        )

    def _request_with_retry(
        self,
        method: str,
        url: str,
        endpoint_type: str = "default",
        **kwargs: Any,
    ) -> requests.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            endpoint_type: Type for rate limiting
            **kwargs: Additional request arguments

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure after retries
        """
        request_headers = kwargs.pop("headers", None) or {}
        headers = self._headers.copy()
        headers.update(request_headers)
        kwargs["headers"] = headers

        timeout = kwargs.pop("timeout", self.timeout)

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                self.api_counter.increment(endpoint_type=endpoint_type)
                response = requests.request(method, url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as exc:
                # Don't retry on 4xx client errors (403 Forbidden, 404 Not Found, etc.)
                # These are expected responses, not transient failures
                if exc.response is not None and 400 <= exc.response.status_code < 500:
                    raise
                last_error = exc
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    self.log_warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait_time}s: {exc}"
                    )
                    time.sleep(wait_time)
            except requests.exceptions.RequestException as exc:
                # Retry on network errors, timeouts, etc.
                last_error = exc
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    self.log_warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait_time}s: {exc}"
                    )
                    time.sleep(wait_time)

        raise last_error  # type: ignore

    # Permission hints for common endpoints (shows where to set permission in Cloudflare dashboard)
    PERMISSION_HINTS: dict[str, str] = {
        # Zone-level permissions
        "settings/ssl": "Zone > Zone Settings > Read",
        "security/events": "Zone > Firewall Services > Read",
        "dns_records": "Zone > DNS > Read",
        "rulesets": "Zone > Config Rules > Read",
        # Account-level permissions
        "d1/database": "Account > D1 > Read",
        "workers/scripts": "Account > Worker Scripts > Read",
        "storage/kv/namespaces": "Account > Workers KV Storage > Read",
        "r2/buckets": "Account > Workers R2 Storage > Read",
        "access/apps": "Account > Access: Apps and Policies > Read",
        "cfd_tunnel": "Account > Cloudflare Tunnel > Read",
        "load_balancers": "Account > Load Balancers > Read",
        "subscriptions": "Account > Billing > Read",
        "pages/projects": "Account > Cloudflare Pages > Read",
    }

    # Service name to required permission mapping (for "unused permission" hints)
    SERVICE_PERMISSIONS: dict[str, str] = {
        "workers": "Account > Worker Scripts > Read",
        "kv": "Account > Workers KV Storage > Read",
        "r2": "Account > Workers R2 Storage > Read",
        "d1": "Account > D1 > Read",
        "access": "Account > Access: Apps and Policies > Read",
        "tunnel": "Account > Cloudflare Tunnel > Read",
        "load_balancer": "Account > Load Balancers > Read",
        "waf": "Zone > Firewall Services > Read (Pro+ only)",
        "ssl": "Zone > Zone Settings > Read",
        "rulesets": "Zone > Config Rules > Read",
        # These use GraphQL analytics - no special permission beyond zone read
        # "zones": base permission
        # "zone_analytics": base permission
        # "dns_analytics": base permission
    }

    def _get_permission_hint(self, endpoint: str) -> str:
        """Get permission hint for an endpoint."""
        for pattern, permission in self.PERMISSION_HINTS.items():
            if pattern in endpoint:
                return f" (needs '{permission}')"
        return ""

    @staticmethod
    def _extract_api_error_details(errors: Any) -> list[tuple[int | None, str]]:
        """Extract (code, message) pairs from a Cloudflare 'errors' list.

        Args:
            errors: Value of the 'errors' field of an API response

        Returns:
            One (code, message) pair per error entry, empty if there are none
        """
        if not isinstance(errors, list):
            return []

        details: list[tuple[int | None, str]] = []
        for error in errors:
            if not isinstance(error, dict):
                details.append((None, str(error)))
                continue
            code = error.get("code")
            message = error.get("message")
            details.append(
                (
                    code if isinstance(code, int) else None,
                    message if isinstance(message, str) and message else str(error),
                )
            )
        return details

    @staticmethod
    def _is_permission_error(error_code: int | None, error_message: str) -> bool:
        """Return True if an API error means the token lacks a permission.

        Cloudflare answers a missing token permission with code 10000
        ("Authentication error") or 9109 ("Unauthorized to access requested resource"),
        so the code counts as well as the message text.

        Args:
            error_code: Cloudflare error code, if any
            error_message: Cloudflare error message

        Returns:
            True for permission-related failures
        """
        if error_code in CLOUDFLARE_PERMISSION_ERROR_CODES:
            return True
        lowered = error_message.lower()
        return any(
            marker in lowered
            for marker in ("permission", "not authorized", "unauthorized", "forbidden")
        )

    @staticmethod
    def _is_invalid_token_error(error_code: int | None, error_message: str) -> bool:
        """Return True if an API error means the token itself is invalid.

        Cloudflare answers zone endpoints with code 9109 "Invalid access token" for an
        invalid token, but uses the same code for a missing permission, so the message
        tells the two apart.

        Args:
            error_code: Cloudflare error code, if any
            error_message: Cloudflare error message

        Returns:
            True for an invalid or expired token
        """
        lowered = error_message.lower()
        return (
            error_code == CLOUDFLARE_ERROR_CODE_UNAUTHORIZED
            and "invalid" in lowered
            and "token" in lowered
        )

    def _add_auth_error(
        self,
        endpoint: str,
        error_details: list[tuple[int | None, str]],
        status_code: int | None = None,
    ) -> bool:
        """Record an invalid-token or permission error, if the response is one.

        Any HTTP 403 counts as a missing permission unless the token itself is invalid.

        Args:
            endpoint: API endpoint that failed
            error_details: (code, message) pairs from the response
            status_code: HTTP status of the response, if it failed

        Returns:
            True if an error was recorded
        """
        if any(self._is_invalid_token_error(code, message) for code, message in error_details):
            self.error_collector.add(
                ERROR_CATEGORY_API, ERROR_SERVICE_REST, f"Invalid API token: {endpoint}"
            )
            return True
        if status_code == 403 or any(
            self._is_permission_error(code, message) for code, message in error_details
        ):
            hint = self._get_permission_hint(endpoint)
            self.error_collector.add(
                ERROR_CATEGORY_API, ERROR_SERVICE_REST, f"Permission denied: {endpoint}{hint}"
            )
            return True
        return False

    @staticmethod
    def _is_transient_status(status_code: int | None) -> bool:
        """Return True if a failed request is likely to succeed on a later run.

        Args:
            status_code: HTTP status of the failed request, None for timeouts and
                network errors (no response)

        Returns:
            True for no response, HTTP 429 and HTTP 5xx
        """
        return status_code is None or status_code == 429 or status_code >= 500

    @staticmethod
    def _format_api_error_message(
        prefix: str,
        endpoint: str,
        status_code: int | None = None,
        error_code: int | None = None,
        error_message: str = "",
    ) -> str:
        """Build standardized API error messages with optional details."""
        details = []
        if status_code is not None:
            details.append(f"HTTP {status_code}")
        if error_code is not None:
            details.append(f"code {error_code}")
        if error_message:
            details.append(f"msg {error_message}")

        if not details:
            return f"{prefix}: {endpoint}"
        return f"{prefix}: {endpoint} ({', '.join(details)})"

    def _rest_get(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Make REST API GET request.

        Args:
            endpoint: API endpoint (without base URL)
            headers: Optional headers to merge with default headers

        Returns:
            Result data from response
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = self._request_with_retry("GET", url, headers=headers)
            data = response.json()

            if data.get("success"):
                return data.get("result", [])

            errors = data.get("errors", [])
            self.log_error(f"API error for {endpoint}: {errors}")
            error_details = self._extract_api_error_details(errors)
            if self._add_auth_error(endpoint, error_details):
                return []
            if not error_details:
                self.error_collector.add(
                    ERROR_CATEGORY_API, ERROR_SERVICE_REST, f"REST API: {endpoint}"
                )
            else:
                for code, message in error_details:
                    self.error_collector.add(
                        ERROR_CATEGORY_API,
                        ERROR_SERVICE_REST,
                        self._format_api_error_message(
                            "REST API",
                            endpoint,
                            error_code=code,
                            error_message=message,
                        ),
                    )
            return []

        except requests.exceptions.RequestException as exc:
            self.log_error(f"Request failed for {endpoint}: {exc}")
            status_code: int | None = None
            error_details = []
            if hasattr(exc, "response") and exc.response is not None:
                status_code = exc.response.status_code
                try:
                    payload = exc.response.json()
                except ValueError:
                    payload = None
                if isinstance(payload, dict):
                    error_details = self._extract_api_error_details(payload.get("errors"))
            error_code, error_message = error_details[0] if error_details else (None, "")

            if not self._add_auth_error(endpoint, error_details, status_code):
                prefix = "Rate limited" if status_code == 429 else "REST API error"
                self.error_collector.add(
                    ERROR_CATEGORY_API,
                    ERROR_SERVICE_REST,
                    self._format_api_error_message(
                        prefix,
                        endpoint,
                        status_code=status_code,
                        error_code=error_code,
                        error_message=error_message,
                    ),
                    transient=self._is_transient_status(status_code),
                )
            return []
        except ValueError as exc:
            self.log_error(f"JSON decode error for {endpoint}: {exc}")
            self.error_collector.add(
                ERROR_CATEGORY_API,
                ERROR_SERVICE_REST,
                f"REST API JSON error: {endpoint}",
                transient=True,
            )
            return []

    def _graphql_query(
        self,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Data from response
        """
        try:
            response = self._request_with_retry(
                "POST",
                self.GRAPHQL_URL,
                endpoint_type=ENDPOINT_TYPE_GRAPHQL,
                json={"query": query, "variables": variables},
            )
            data = response.json()

            if data.get("errors"):
                for error in data["errors"]:
                    error_msg = error.get("message", str(error))
                    self.log_error(f"GraphQL error: {error_msg}")
                    self.error_collector.add(
                        ERROR_CATEGORY_API, ERROR_SERVICE_GRAPHQL, f"GraphQL: {error_msg}"
                    )

            return data.get("data") or {}

        except requests.exceptions.RequestException as exc:
            self.log_error(f"GraphQL request failed: {exc}")
            status_code = exc.response.status_code if exc.response is not None else None
            self.error_collector.add(
                ERROR_CATEGORY_API,
                ERROR_SERVICE_GRAPHQL,
                f"GraphQL request failed: {exc}",
                transient=self._is_transient_status(status_code),
            )
            return {}
        except ValueError as exc:
            self.log_error(f"GraphQL JSON decode error: {exc}")
            self.error_collector.add(
                ERROR_CATEGORY_API,
                ERROR_SERVICE_GRAPHQL,
                f"GraphQL JSON decode error: {exc}",
                transient=True,
            )
            return {}

    def get_and_clear_errors(self) -> list[dict[str, str | float]]:
        """Return collected errors and clear the collection.

        Returns:
            List of error dictionaries with category, service, message, timestamp
        """
        return self.error_collector.get_and_clear()

    # =========================================================================
    # REST API Methods - Resource Discovery
    # =========================================================================

    def list_workers(self) -> list[dict[str, Any]]:
        """List all Workers scripts.

        Returns:
            List of worker script objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/workers/scripts")
        return result if isinstance(result, list) else []

    def list_kv_namespaces(self) -> list[dict[str, Any]]:
        """List all KV namespaces.

        Returns:
            List of KV namespace objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/storage/kv/namespaces")
        return result if isinstance(result, list) else []

    def list_zones(self) -> list[dict[str, Any]]:
        """List all DNS zones.

        Returns:
            List of zone objects
        """
        result = self._rest_get("zones")
        return result if isinstance(result, list) else []

    def list_r2_buckets(self, jurisdiction: str | None = None) -> list[dict[str, Any]]:
        """List all R2 buckets.

        Args:
            jurisdiction: Optional jurisdiction (e.g., "eu") to list buckets from

        Returns:
            List of R2 bucket objects
        """
        headers = {}
        if jurisdiction:
            headers["cf-r2-jurisdiction"] = jurisdiction

        result = self._rest_get(
            f"accounts/{self.account_id}/r2/buckets",
            headers=headers if headers else None,
        )
        # R2 API wraps buckets in a "buckets" key
        if isinstance(result, dict):
            return result.get("buckets", [])
        return result if isinstance(result, list) else []

    def list_zone_rulesets(self, zone_id: str) -> list[dict[str, Any]]:
        """List rulesets for a zone.

        Args:
            zone_id: Zone ID

        Returns:
            List of ruleset objects with id, name, kind, phase, version
        """
        result = self._rest_get(f"zones/{zone_id}/rulesets")
        return result if isinstance(result, list) else []

    def list_access_apps(self) -> list[dict[str, Any]]:
        """List Cloudflare Access applications.

        Returns:
            List of Access application objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/access/apps")
        return result if isinstance(result, list) else []

    def list_access_policies(self, app_id: str) -> list[dict[str, Any]]:
        """List policies for an Access application.

        Args:
            app_id: Access application ID

        Returns:
            List of policy objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/access/apps/{app_id}/policies")
        return result if isinstance(result, list) else []

    def list_tunnels(self) -> list[dict[str, Any]]:
        """List Cloudflare Tunnels.

        Returns:
            List of tunnel objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/cfd_tunnel")
        return result if isinstance(result, list) else []

    def get_tunnel_connections(self, tunnel_id: str) -> list[dict[str, Any]]:
        """Get connections for a tunnel.

        Args:
            tunnel_id: Tunnel ID

        Returns:
            List of connection objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/cfd_tunnel/{tunnel_id}/connections")
        return result if isinstance(result, list) else []

    def list_load_balancers(self, zone_id: str) -> list[dict[str, Any]]:
        """List load balancers for a zone.

        Args:
            zone_id: Zone ID

        Returns:
            List of load balancer objects
        """
        result = self._rest_get(f"zones/{zone_id}/load_balancers")
        return result if isinstance(result, list) else []

    def list_load_balancer_pools(self) -> list[dict[str, Any]]:
        """List all load balancer pools.

        Returns:
            List of pool objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/load_balancers/pools")
        return result if isinstance(result, list) else []

    def get_pool_health(self, pool_id: str) -> dict[str, Any]:
        """Get health status for a load balancer pool.

        Args:
            pool_id: Pool ID

        Returns:
            Pool health data
        """
        result = self._rest_get(f"accounts/{self.account_id}/load_balancers/pools/{pool_id}/health")
        return result if isinstance(result, dict) else {}

    def fetch_waf_analytics(
        self,
        zone_ids: list[str],
        zone_plans: dict[str, str] | None = None,
        zone_names: dict[str, str] | None = None,
        timeframe: str = "24h",
    ) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """Fetch WAF/firewall events via GraphQL.

        Uses parallel execution for multiple zones.

        Args:
            zone_ids: List of zone IDs
            zone_plans: Optional mapping of zone_id -> plan name (e.g., "Free", "Pro")
            zone_names: Optional mapping of zone_id -> zone name (for skipped info)
            timeframe: Time range for analytics

        Returns:
            Tuple of:
            - Dictionary mapping zone ID to WAF analytics:
              {zone_id: {"total": X, "blocked": Y, "challenged": Z}}
            - List of zone names that were skipped (Free plan)
        """
        if not zone_ids:
            return {}, []

        start_time, end_time = self._get_time_range(timeframe)
        plans = zone_plans or {}
        names = zone_names or {}

        query = """
        query FirewallEvents($zoneTag: String!, $since: Time!, $until: Time!) {
          viewer {
            zones(filter: {zoneTag: $zoneTag}) {
              firewallEventsAdaptiveGroups(
                limit: 100
                filter: {datetime_geq: $since, datetime_lt: $until}
              ) {
                dimensions {
                  action
                }
                count
              }
            }
          }
        }
        """

        def fetch_single_zone_waf(single_zone_id: str) -> tuple[dict[str, Any], str | None]:
            """Fetch WAF analytics for a single zone.

            Returns:
                Tuple of (analytics_dict, skipped_zone_name or None)
            """
            # Check if zone has Pro+ plan (required for firewallEventsAdaptiveGroups)
            zone_plan = plans.get(single_zone_id) or "Free"
            is_pro_plus = "free" not in zone_plan.lower()

            if not is_pro_plus:
                # Free Zone -> skip GraphQL query, return 0 events
                zone_name = names.get(single_zone_id, single_zone_id)
                return {"total": 0, "blocked": 0, "challenged": 0}, zone_name

            variables = {
                "zoneTag": single_zone_id,
                "since": start_time,
                "until": end_time,
            }

            data = self._graphql_query(query, variables)

            total_events = 0
            blocked_events = 0
            challenged_events = 0

            zones = data.get("viewer", {}).get("zones", [])
            if zones:
                groups = zones[0].get("firewallEventsAdaptiveGroups", [])
                for group in groups:
                    count = group.get("count", 0)
                    action = group.get("dimensions", {}).get("action", "").lower()

                    total_events += count

                    if action in ("block", "drop"):
                        blocked_events += count
                    elif action in (
                        "challenge",
                        "jschallenge",
                        "managedchallenge",
                        "managed_challenge",
                    ):
                        challenged_events += count

            return {
                "total": total_events,
                "blocked": blocked_events,
                "challenged": challenged_events,
            }, None

        # Parallel execution for all zones
        results = parallel_map(fetch_single_zone_waf, zone_ids, logger=self)

        # Convert results, collecting skipped zones
        analytics: dict[str, dict[str, Any]] = {}
        skipped_zones: list[str] = []
        empty_analytics = {"total": 0, "blocked": 0, "challenged": 0}

        for zone_key, zone_result in results.items():
            if zone_result is None:
                analytics[zone_key] = empty_analytics.copy()
            else:
                zone_analytics, skipped_name = zone_result
                analytics[zone_key] = zone_analytics
                if skipped_name:
                    skipped_zones.append(skipped_name)

        return analytics, skipped_zones

    def get_account_subscriptions(self) -> list[dict[str, Any]]:
        """Get account subscriptions to determine plan type.

        Returns:
            List of subscription objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/subscriptions")
        return result if isinstance(result, list) else []

    def is_workers_paid_plan(self) -> bool:
        """Check if account has Workers paid plan.

        Returns:
            True if paid plan, False if free plan (also defaults to False on API errors)
        """
        try:
            subscriptions = self.get_account_subscriptions()
            if not subscriptions:
                # No subscriptions data (API error or no permission) - assume free plan
                return False
            for sub in subscriptions:
                rate_plan = sub.get("rate_plan", {})
                plan_id = rate_plan.get("id", "").lower()
                # Check for workers paid plans
                if "workers" in plan_id and (
                    "paid" in plan_id or "standard" in plan_id or "bundled" in plan_id
                ):
                    return True
        except (requests.RequestException, AttributeError, TypeError, ValueError) as exc:
            self.log_warning(f"Could not determine Workers plan type: {exc}, assuming free plan")
        return False

    # =========================================================================
    # GraphQL API Methods - Analytics
    # =========================================================================

    def fetch_workers_analytics(
        self,
        worker_names: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch Workers analytics via GraphQL.

        Uses parallel execution for multiple workers.

        Args:
            worker_names: List of worker script names
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping worker name to analytics data
        """
        if not worker_names:
            return {}

        start_time, end_time = self._get_time_range(timeframe)

        def fetch_single_worker(current_worker_name: str) -> dict[str, Any]:
            """Fetch analytics for a single worker."""
            query = """
            query GetWorkersAnalytics($accountTag: String!, $datetimeStart: Time!, $datetimeEnd: Time!, $scriptName: String!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  workersInvocationsAdaptive(
                    limit: 1000
                    filter: {
                      scriptName: $scriptName
                      datetime_geq: $datetimeStart
                      datetime_leq: $datetimeEnd
                    }
                  ) {
                    sum {
                      requests
                      subrequests
                      errors
                    }
                    quantiles {
                      cpuTimeP50
                      cpuTimeP90
                      cpuTimeP99
                      cpuTimeP999
                      wallTimeP50
                      wallTimeP90
                      wallTimeP99
                      wallTimeP999
                      requestDurationP50
                      requestDurationP90
                      requestDurationP99
                      requestDurationP999
                    }
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "datetimeStart": start_time,
                "datetimeEnd": end_time,
                "scriptName": current_worker_name,
            }

            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            # Default empty analytics
            empty_analytics = {
                "requests": 0,
                "errors": 0,
                "cpu_time_p50": 0,
                "cpu_time_p90": 0,
                "cpu_time_p99": 0,
                "cpu_time_p999": 0,
                "wall_time_p50": 0,
                "wall_time_p90": 0,
                "wall_time_p99": 0,
                "wall_time_p999": 0,
                "duration_p50": 0,
                "duration_p90": 0,
                "duration_p99": 0,
                "duration_p999": 0,
            }

            if not accounts:
                return empty_analytics

            invocations = accounts[0].get("workersInvocationsAdaptive", [])
            if not invocations:
                return empty_analytics

            total_requests = 0
            total_errors = 0
            # Collect all quantile values with request counts for weighted averaging
            quantile_values: dict[str, list[tuple[float, int]]] = {
                "cpu_time_p50": [],  # (value, request_count)
                "cpu_time_p90": [],
                "cpu_time_p99": [],
                "cpu_time_p999": [],
                "wall_time_p50": [],
                "wall_time_p90": [],
                "wall_time_p99": [],
                "wall_time_p999": [],
                "request_duration_p50": [],
                "request_duration_p90": [],
                "request_duration_p99": [],
                "request_duration_p999": [],
            }

            for inv in invocations:
                sum_data = inv.get("sum", {})
                quantiles = inv.get("quantiles", {})

                request_count = sum_data.get("requests", 0)
                total_requests += request_count
                total_errors += sum_data.get("errors", 0)

                # Only include quantiles if we have requests (for weighted average)
                if request_count > 0:
                    # CPU Time (in microseconds from API)
                    if quantiles.get("cpuTimeP50"):
                        quantile_values["cpu_time_p50"].append(
                            (quantiles["cpuTimeP50"], request_count)
                        )
                    if quantiles.get("cpuTimeP90"):
                        quantile_values["cpu_time_p90"].append(
                            (quantiles["cpuTimeP90"], request_count)
                        )
                    if quantiles.get("cpuTimeP99"):
                        quantile_values["cpu_time_p99"].append(
                            (quantiles["cpuTimeP99"], request_count)
                        )
                    if quantiles.get("cpuTimeP999"):
                        quantile_values["cpu_time_p999"].append(
                            (quantiles["cpuTimeP999"], request_count)
                        )
                    # Wall Time (in microseconds from API) - includes ctx.waitUntil
                    if quantiles.get("wallTimeP50"):
                        quantile_values["wall_time_p50"].append(
                            (quantiles["wallTimeP50"], request_count)
                        )
                    if quantiles.get("wallTimeP90"):
                        quantile_values["wall_time_p90"].append(
                            (quantiles["wallTimeP90"], request_count)
                        )
                    if quantiles.get("wallTimeP99"):
                        quantile_values["wall_time_p99"].append(
                            (quantiles["wallTimeP99"], request_count)
                        )
                    if quantiles.get("wallTimeP999"):
                        quantile_values["wall_time_p999"].append(
                            (quantiles["wallTimeP999"], request_count)
                        )
                    # Request Duration (in microseconds from API) - response time
                    if quantiles.get("requestDurationP50"):
                        quantile_values["request_duration_p50"].append(
                            (quantiles["requestDurationP50"], request_count)
                        )
                    if quantiles.get("requestDurationP90"):
                        quantile_values["request_duration_p90"].append(
                            (quantiles["requestDurationP90"], request_count)
                        )
                    if quantiles.get("requestDurationP99"):
                        quantile_values["request_duration_p99"].append(
                            (quantiles["requestDurationP99"], request_count)
                        )
                    if quantiles.get("requestDurationP999"):
                        quantile_values["request_duration_p999"].append(
                            (quantiles["requestDurationP999"], request_count)
                        )

            return {
                "requests": total_requests,
                "errors": total_errors,
                "cpu_time_p50": _weighted_avg(quantile_values["cpu_time_p50"], to_ms=True),
                "cpu_time_p90": _weighted_avg(quantile_values["cpu_time_p90"], to_ms=True),
                "cpu_time_p99": _weighted_avg(quantile_values["cpu_time_p99"], to_ms=True),
                "cpu_time_p999": _weighted_avg(quantile_values["cpu_time_p999"], to_ms=True),
                "wall_time_p50": _weighted_avg(quantile_values["wall_time_p50"], to_ms=True),
                "wall_time_p90": _weighted_avg(quantile_values["wall_time_p90"], to_ms=True),
                "wall_time_p99": _weighted_avg(quantile_values["wall_time_p99"], to_ms=True),
                "wall_time_p999": _weighted_avg(quantile_values["wall_time_p999"], to_ms=True),
                # Request Duration (like in Cloudflare Dashboard)
                "duration_p50": _weighted_avg(quantile_values["request_duration_p50"], to_ms=True),
                "duration_p90": _weighted_avg(quantile_values["request_duration_p90"], to_ms=True),
                "duration_p99": _weighted_avg(quantile_values["request_duration_p99"], to_ms=True),
                "duration_p999": _weighted_avg(
                    quantile_values["request_duration_p999"], to_ms=True
                ),
            }

        # Parallel execution for all workers
        results = parallel_map(fetch_single_worker, worker_names, logger=self)

        # Convert results, handling None for failed fetches
        analytics: dict[str, dict[str, Any]] = {}
        for worker_key, worker_result in results.items():
            if worker_result is None:
                analytics[worker_key] = {
                    "requests": 0,
                    "errors": 0,
                    "cpu_time_p50": 0,
                    "cpu_time_p90": 0,
                    "cpu_time_p99": 0,
                    "cpu_time_p999": 0,
                    "wall_time_p50": 0,
                    "wall_time_p90": 0,
                    "wall_time_p99": 0,
                    "wall_time_p999": 0,
                    "duration_p50": 0,
                    "duration_p90": 0,
                    "duration_p99": 0,
                    "duration_p999": 0,
                }
            else:
                analytics[worker_key] = worker_result

        return analytics

    def fetch_workers_daily_usage(self) -> dict[str, Any]:
        """Fetch total workers requests since midnight UTC.

        Returns:
            Dictionary with daily usage data:
            - requests_today: Total requests since midnight UTC
            - daily_limit: Request limit (100000 for free, 0 for unlimited/paid)
            - is_paid_plan: Whether account has paid plan
            - per_worker: Dict mapping worker name to request count
        """
        # Get midnight UTC today
        now = datetime.now(timezone.utc)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        start_time = midnight.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Query all workers requests since midnight (no scriptName filter)
        query = """
        query GetWorkersDailyUsage($accountTag: String!, $datetimeStart: Time!, $datetimeEnd: Time!) {
          viewer {
            accounts(filter: {accountTag: $accountTag}) {
              workersInvocationsAdaptive(
                limit: 10000
                filter: {
                  datetime_geq: $datetimeStart
                  datetime_leq: $datetimeEnd
                }
              ) {
                sum {
                  requests
                }
                dimensions {
                  scriptName
                }
              }
            }
          }
        }
        """

        variables = {
            "accountTag": self.account_id,
            "datetimeStart": start_time,
            "datetimeEnd": end_time,
        }

        data = self._graphql_query(query, variables)
        accounts = data.get("viewer", {}).get("accounts", [])

        total_requests = 0
        per_worker: dict[str, int] = {}

        if accounts:
            invocations = accounts[0].get("workersInvocationsAdaptive", [])
            for inv in invocations:
                sum_data = inv.get("sum", {})
                dimensions = inv.get("dimensions", {})

                request_count = sum_data.get("requests", 0)
                script_name = dimensions.get("scriptName", "unknown")

                total_requests += request_count
                per_worker[script_name] = per_worker.get(script_name, 0) + request_count

        # Determine plan type and limit
        is_paid = self.is_workers_paid_plan()
        daily_limit = 0 if is_paid else FREE_PLAN_DAILY_LIMIT  # 0 = unlimited

        return {
            "requests_today": total_requests,
            "daily_limit": daily_limit,
            "is_paid_plan": is_paid,
            "per_worker": per_worker,
        }

    def fetch_workers_monthly_usage(self) -> dict[str, Any]:
        """Fetch total workers usage since start of current billing period.

        Returns:
            Dictionary with monthly usage data:
            - requests_month: Total requests this month
            - cpu_time_ms: Estimated total CPU time in milliseconds (requests * avg CPU time)
        """
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        start_time = month_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Note: cpuTime is not available as sum field, so we use P50 quantile
        # and multiply by requests to estimate total CPU time
        query = """
        query GetWorkersMonthlyUsage($accountTag: String!, $datetimeStart: Time!, $datetimeEnd: Time!) {
          viewer {
            accounts(filter: {accountTag: $accountTag}) {
              workersInvocationsAdaptive(
                limit: 10000
                filter: {
                  datetime_geq: $datetimeStart
                  datetime_leq: $datetimeEnd
                }
              ) {
                sum {
                  requests
                }
                quantiles {
                  cpuTimeP50
                }
              }
            }
          }
        }
        """

        variables = {
            "accountTag": self.account_id,
            "datetimeStart": start_time,
            "datetimeEnd": end_time,
        }

        data = self._graphql_query(query, variables)
        accounts = data.get("viewer", {}).get("accounts", [])

        total_requests = 0
        total_cpu_time_ms = 0.0

        if accounts:
            invocations = accounts[0].get("workersInvocationsAdaptive", [])
            for inv in invocations:
                sum_data = inv.get("sum", {})
                quantiles = inv.get("quantiles", {})

                request_count = sum_data.get("requests", 0)
                cpu_p50 = quantiles.get("cpuTimeP50", 0)  # in microseconds

                total_requests += request_count
                # Estimate total CPU time: request_count * median CPU time per request
                # Convert µs to ms
                total_cpu_time_ms += (request_count * cpu_p50) / 1000

        return {
            "requests_month": total_requests,
            "cpu_time_ms": total_cpu_time_ms,
        }

    def fetch_kv_analytics(
        self,
        namespace_ids: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch KV namespace analytics via GraphQL.

        Uses parallel execution for multiple namespaces.

        Args:
            namespace_ids: List of namespace IDs
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping namespace ID to analytics data
        """
        if not namespace_ids:
            return {}

        start_date, end_date = self._get_date_range(timeframe)

        def fetch_single_namespace(current_ns_id: str) -> dict[str, Any]:
            """Fetch analytics for a single KV namespace."""
            ns_analytics: dict[str, Any] = {
                "reads": 0,
                "writes": 0,
                "deletes": 0,
                "lists": 0,
                "key_count": 0,
                "storage_bytes": 0,
                # Latency quantiles (matching Cloudflare dashboard: P50, P75, P90, P99)
                "latency_p50": 0.0,
                "latency_p75": 0.0,
                "latency_p90": 0.0,
                "latency_p99": 0.0,
            }

            query = """
            query GetKVOperations($accountTag: String!, $namespaceId: String!, $dateStart: Date!, $dateEnd: Date!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  kvOperationsAdaptiveGroups(
                    filter: {
                      namespaceId: $namespaceId
                      date_geq: $dateStart
                      date_leq: $dateEnd
                    }
                    limit: 1000
                  ) {
                    sum {
                      requests
                    }
                    dimensions {
                      actionType
                    }
                    quantiles {
                      latencyMsP50
                      latencyMsP75
                      latencyMsP90
                      latencyMsP99
                    }
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "namespaceId": current_ns_id,
                "dateStart": start_date,
                "dateEnd": end_date,
            }

            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            if accounts:
                ops_groups = accounts[0].get("kvOperationsAdaptiveGroups", [])

                # Collect latency values for weighted averaging
                latency_values: dict[str, list[tuple[float, int]]] = {
                    "latency_p50": [],
                    "latency_p75": [],
                    "latency_p90": [],
                    "latency_p99": [],
                }

                for group in ops_groups:
                    action_type = group.get("dimensions", {}).get("actionType", "").lower()
                    requests_count = group.get("sum", {}).get("requests", 0)
                    quantiles = group.get("quantiles", {})

                    if action_type == "read":
                        ns_analytics["reads"] += requests_count
                    elif action_type == "write":
                        ns_analytics["writes"] += requests_count
                    elif action_type == "delete":
                        ns_analytics["deletes"] += requests_count
                    elif action_type == "list":
                        ns_analytics["lists"] += requests_count

                    # Collect latency quantiles (weighted by request count)
                    if requests_count > 0:
                        if quantiles.get("latencyMsP50"):
                            latency_values["latency_p50"].append(
                                (quantiles["latencyMsP50"], requests_count)
                            )
                        if quantiles.get("latencyMsP75"):
                            latency_values["latency_p75"].append(
                                (quantiles["latencyMsP75"], requests_count)
                            )
                        if quantiles.get("latencyMsP90"):
                            latency_values["latency_p90"].append(
                                (quantiles["latencyMsP90"], requests_count)
                            )
                        if quantiles.get("latencyMsP99"):
                            latency_values["latency_p99"].append(
                                (quantiles["latencyMsP99"], requests_count)
                            )

                ns_analytics["latency_p50"] = _weighted_avg(latency_values["latency_p50"])
                ns_analytics["latency_p75"] = _weighted_avg(latency_values["latency_p75"])
                ns_analytics["latency_p90"] = _weighted_avg(latency_values["latency_p90"])
                ns_analytics["latency_p99"] = _weighted_avg(latency_values["latency_p99"])

            # Fetch storage snapshot (key count + bytes). These are daily values, so look at
            # the last 24h and take the newest day; shorter windows can miss today's snapshot.
            storage_start, storage_end = self._get_date_range(TIMEFRAME_24H)
            storage_query = """
            query GetKVStorage($accountTag: String!, $namespaceId: String!, $dateStart: Date!, $dateEnd: Date!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  kvStorageAdaptiveGroups(
                    filter: {
                      namespaceId: $namespaceId
                      date_geq: $dateStart
                      date_leq: $dateEnd
                    }
                    limit: 1
                    orderBy: [date_DESC]
                  ) {
                    max {
                      keyCount
                      byteCount
                    }
                    dimensions {
                      date
                    }
                  }
                }
              }
            }
            """

            storage_variables = {**variables, "dateStart": storage_start, "dateEnd": storage_end}
            storage_data = self._graphql_query(storage_query, storage_variables)
            storage_accounts = (storage_data.get("viewer") or {}).get("accounts", [])

            if storage_accounts:
                storage_groups = storage_accounts[0].get("kvStorageAdaptiveGroups", [])
                if storage_groups:
                    storage_max = storage_groups[0].get("max") or {}
                    ns_analytics["key_count"] = storage_max.get("keyCount") or 0
                    ns_analytics["storage_bytes"] = storage_max.get("byteCount") or 0

            return ns_analytics

        # Parallel execution for all namespaces
        results = parallel_map(fetch_single_namespace, namespace_ids, logger=self)

        # Convert results, handling None for failed fetches
        analytics: dict[str, dict[str, Any]] = {}
        empty_analytics = {
            "reads": 0,
            "writes": 0,
            "deletes": 0,
            "lists": 0,
            "key_count": 0,
            "storage_bytes": 0,
            "latency_p50": 0.0,
            "latency_p75": 0.0,
            "latency_p90": 0.0,
            "latency_p99": 0.0,
        }
        for ns_key, ns_result in results.items():
            analytics[ns_key] = (
                ns_result if ns_result is not None else empty_analytics.copy()
            )

        return analytics

    def fetch_kv_read_status(
        self,
        namespace_ids: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, int]]:
        """Fetch KV read status (hot/cold/not_found) via GraphQL.

        Uses parallel execution for multiple namespaces.

        Args:
            namespace_ids: List of namespace IDs
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping namespace ID to read status counts
            e.g., {"ns_id": {"hot_read": 100, "cold_read": 50, "not_found": 5}}
        """
        if not namespace_ids:
            return {}

        start_date, end_date = self._get_date_range(timeframe)

        def fetch_single_namespace_status(current_ns_id: str) -> dict[str, int]:
            """Fetch read status for a single namespace."""
            query = """
            query KVReadStatus($accountTag: String!, $namespaceId: String!, $dateStart: Date!, $dateEnd: Date!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  kvOperationsAdaptiveGroups(
                    limit: 10000
                    filter: {
                      namespaceId: $namespaceId
                      date_geq: $dateStart
                      date_leq: $dateEnd
                      actionType: "read"
                    }
                  ) {
                    count
                    dimensions {
                      result
                    }
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "namespaceId": current_ns_id,
                "dateStart": start_date,
                "dateEnd": end_date,
            }

            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            ns_status: dict[str, int] = {
                "hot_read": 0,
                "cold_read": 0,
                "not_found": 0,
            }

            if accounts:
                ops_groups = accounts[0].get("kvOperationsAdaptiveGroups", [])
                for group in ops_groups:
                    read_result = group.get("dimensions", {}).get("result", "")
                    count = group.get("count", 0)

                    if read_result == "hot_read":
                        ns_status["hot_read"] += count
                    elif read_result == "cold_read":
                        ns_status["cold_read"] += count
                    elif read_result == "not_found":
                        ns_status["not_found"] += count

            return ns_status

        # Parallel execution for all namespaces
        results = parallel_map(fetch_single_namespace_status, namespace_ids, logger=self)

        # Convert results, handling None for failed fetches
        empty_status: dict[str, int] = {"hot_read": 0, "cold_read": 0, "not_found": 0}
        analytics: dict[str, dict[str, int]] = {}
        for ns_key, ns_result in results.items():
            analytics[ns_key] = ns_result if ns_result is not None else empty_status.copy()

        return analytics

    def fetch_kv_monthly_summary(
        self,
        namespace_ids: list[str],
    ) -> dict[str, dict[str, int]]:
        """Fetch KV operations since start of current month.

        Uses parallel execution for multiple namespaces.

        Args:
            namespace_ids: List of namespace IDs

        Returns:
            Dictionary mapping namespace ID to monthly operation counts
            e.g., {"ns_id": {"reads": 8870, "writes": 896, "lists": 214, "deletes": 0}}
        """
        if not namespace_ids:
            return {}

        # Get month start and current date
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        start_date = month_start.strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        def fetch_single_namespace_monthly(current_ns_id: str) -> dict[str, int]:
            """Fetch monthly summary for a single namespace."""
            query = """
            query KVMonthlySummary($accountTag: String!, $namespaceId: String!, $dateStart: Date!, $dateEnd: Date!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  kvOperationsAdaptiveGroups(
                    limit: 10000
                    filter: {
                      namespaceId: $namespaceId
                      date_geq: $dateStart
                      date_leq: $dateEnd
                    }
                  ) {
                    count
                    dimensions {
                      actionType
                    }
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "namespaceId": current_ns_id,
                "dateStart": start_date,
                "dateEnd": end_date,
            }

            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            ns_monthly: dict[str, int] = {
                "reads": 0,
                "writes": 0,
                "lists": 0,
                "deletes": 0,
            }

            if accounts:
                ops_groups = accounts[0].get("kvOperationsAdaptiveGroups", [])
                for group in ops_groups:
                    action_type = group.get("dimensions", {}).get("actionType", "").lower()
                    count = group.get("count", 0)

                    if action_type == "read":
                        ns_monthly["reads"] += count
                    elif action_type == "write":
                        ns_monthly["writes"] += count
                    elif action_type == "list":
                        ns_monthly["lists"] += count
                    elif action_type == "delete":
                        ns_monthly["deletes"] += count

            return ns_monthly

        # Parallel execution for all namespaces
        results = parallel_map(fetch_single_namespace_monthly, namespace_ids, logger=self)

        # Convert results, handling None for failed fetches
        empty_monthly: dict[str, int] = {"reads": 0, "writes": 0, "lists": 0, "deletes": 0}
        analytics: dict[str, dict[str, int]] = {}
        for ns_key, ns_result in results.items():
            analytics[ns_key] = (
                ns_result if ns_result is not None else empty_monthly.copy()
            )

        return analytics

    def fetch_kv_account_usage(
        self,
        namespace_ids: list[str],
    ) -> dict[str, Any]:
        """Fetch KV account-wide daily usage and monitoring thresholds.

        Args:
            namespace_ids: List of namespace IDs to aggregate

        Returns:
            Dictionary with usage and limit data:
            - daily_reads, daily_writes, daily_deletes, daily_lists
            - reads_limit, writes_limit, deletes_limit, lists_limit
            - max_storage
            - total_namespaces
            - is_paid_plan
        """
        # Query GraphQL for today's operations across ALL namespaces
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        daily_reads = 0
        daily_writes = 0
        daily_deletes = 0
        daily_lists = 0

        if namespace_ids:
            query = """
            query KVDailyUsage($accountTag: String!, $date: Date!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  kvOperationsAdaptiveGroups(
                    limit: 10000
                    filter: {
                      date_geq: $date
                      date_leq: $date
                    }
                  ) {
                    count
                    dimensions {
                      actionType
                    }
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "date": today,
            }

            try:
                data = self._graphql_query(query, variables)
                accounts = data.get("viewer", {}).get("accounts", [])

                if accounts:
                    groups = accounts[0].get("kvOperationsAdaptiveGroups", [])
                    for group in groups:
                        action_type = group.get("dimensions", {}).get("actionType", "").lower()
                        count = group.get("count", 0)

                        if action_type == "read":
                            daily_reads += count
                        elif action_type == "write":
                            daily_writes += count
                        elif action_type == "list":
                            daily_lists += count
                        elif action_type == "delete":
                            daily_deletes += count
            except Exception as exc:
                self.log_warning(f"Could not fetch KV daily usage: {exc}")

        # Determine plan limits
        is_paid = self.is_workers_paid_plan()

        if is_paid:
            reads_limit = KV_PAID_MONTHLY_READS
            writes_limit = KV_PAID_MONTHLY_WRITES
            deletes_limit = KV_PAID_MONTHLY_DELETES
            lists_limit = KV_PAID_MONTHLY_LISTS
            max_storage = KV_PAID_MAX_STORAGE
        else:
            reads_limit = KV_FREE_DAILY_READS
            writes_limit = KV_FREE_DAILY_WRITES
            deletes_limit = KV_FREE_DAILY_DELETES
            lists_limit = KV_FREE_DAILY_LISTS
            max_storage = KV_FREE_MAX_STORAGE

        return {
            "daily_reads": daily_reads,
            "daily_writes": daily_writes,
            "daily_deletes": daily_deletes,
            "daily_lists": daily_lists,
            "reads_limit": reads_limit,
            "writes_limit": writes_limit,
            "deletes_limit": deletes_limit,
            "lists_limit": lists_limit,
            "total_namespaces": len(namespace_ids),
            "max_storage": max_storage,
            "is_paid_plan": is_paid,
        }

    def fetch_zone_analytics(
        self,
        zone_ids: list[str],
        zone_plans: dict[str, str] | None = None,
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch zone analytics via GraphQL.

        Uses parallel execution for multiple zones.

        Args:
            zone_ids: List of zone IDs
            zone_plans: Optional mapping of zone_id -> plan name (e.g., "Free", "Pro")
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping zone ID to analytics data
        """
        if not zone_ids:
            return {}

        # Calculate time ranges with adjustment for hourly buckets
        minutes = TIMEFRAME_MINUTES.get(timeframe, 1440)
        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(minutes=minutes)
        end_dt = now

        # Current hour start (for ensuring httpRequests1hGroups coverage)
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        # Calculate adjusted start time for 1h groups
        # If normal start time is after current hour start, we need to go back
        # to just before current hour to capture the current hour's bucket
        if start_dt > current_hour:
            # -1 second to satisfy datetime_gt (strictly greater)
            adjusted_start_dt = current_hour - timedelta(seconds=1)
        else:
            adjusted_start_dt = start_dt

        # Format times
        original_start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        adjusted_start_time = adjusted_start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        plans = zone_plans or {}

        # Basic query for Free zones (no Pro+ metrics)
        # Uses httpRequests1hGroups which requires adjusted start time
        query_basic = """
        query ZoneAnalytics($zoneTag: String!, $since: Time!, $until: Time!) {
          viewer {
            zones(filter: {zoneTag: $zoneTag}) {
              httpRequests1hGroups(limit: 100, filter: {datetime_gt: $since, datetime_lt: $until}) {
                sum {
                  requests
                  bytes
                  threats
                  pageViews
                  cachedRequests
                  cachedBytes
                }
              }
            }
          }
        }
        """

        # Full query for Pro+ zones (includes performance metrics)
        # Uses adjusted start time for 1h groups, but original start time for Adaptive groups
        query_pro = """
        query ZoneAnalytics($zoneTag: String!, $sinceBasic: Time!, $sinceAdaptive: Time!, $until: Time!) {
          viewer {
            zones(filter: {zoneTag: $zoneTag}) {
              httpRequests1hGroups(limit: 100, filter: {datetime_gt: $sinceBasic, datetime_lt: $until}) {
                sum {
                  requests
                  bytes
                  threats
                  pageViews
                  cachedRequests
                  cachedBytes
                }
              }
              httpRequestsAdaptiveGroups(limit: 1000, filter: {datetime_gt: $sinceAdaptive, datetime_lt: $until}) {
                count
                avg {
                  sampleInterval
                }
                quantiles {
                  edgeTimeToFirstByteMsP50
                  edgeTimeToFirstByteMsP95
                  edgeTimeToFirstByteMsP99
                  originResponseDurationMsP50
                  originResponseDurationMsP95
                  originResponseDurationMsP99
                  edgeDnsResponseTimeMsP50
                  edgeDnsResponseTimeMsP95
                  edgeDnsResponseTimeMsP99
                }
              }
            }
          }
        }
        """

        # Default empty analytics
        empty_analytics = {
            "requests": 0,
            "bandwidth": 0,
            "threats": 0,
            "page_views": 0,
            "cached_requests": 0,
            "cached_bandwidth": 0,
            "ttfb_p50": 0.0,
            "ttfb_p95": 0.0,
            "ttfb_p99": 0.0,
            "origin_response_p50": 0.0,
            "origin_response_p95": 0.0,
            "origin_response_p99": 0.0,
            "edge_dns_p50": 0.0,
            "edge_dns_p95": 0.0,
            "edge_dns_p99": 0.0,
        }

        def fetch_single_zone(current_zone_id: str) -> dict[str, Any]:
            """Fetch analytics for a single zone."""
            # Determine if zone has Pro+ plan
            zone_plan = plans.get(current_zone_id) or "Free"  # Handle None values
            is_pro_plus = "free" not in zone_plan.lower()  # Check contains, not exact match

            if is_pro_plus:
                query = query_pro
                variables = {
                    "zoneTag": current_zone_id,
                    "sinceBasic": adjusted_start_time,
                    "sinceAdaptive": original_start_time,
                    "until": end_time,
                }
            else:
                query = query_basic
                variables = {
                    "zoneTag": current_zone_id,
                    "since": adjusted_start_time,
                    "until": end_time,
                }

            data = self._graphql_query(query, variables)
            zones = data.get("viewer", {}).get("zones", [])

            zone_analytics: dict[str, Any] = {
                "requests": 0,
                "bandwidth": 0,
                "threats": 0,
                "page_views": 0,
                "cached_requests": 0,
                "cached_bandwidth": 0,
                # Performance metrics (TTFB, Origin Response, Edge DNS)
                "ttfb_p50": 0.0,
                "ttfb_p95": 0.0,
                "ttfb_p99": 0.0,
                "origin_response_p50": 0.0,
                "origin_response_p95": 0.0,
                "origin_response_p99": 0.0,
                "edge_dns_p50": 0.0,
                "edge_dns_p95": 0.0,
                "edge_dns_p99": 0.0,
            }

            if not zones:
                return zone_analytics

            zone_data = zones[0]

            # Basic analytics from httpRequests1hGroups
            for group in zone_data.get("httpRequests1hGroups", []):
                sum_data = group.get("sum", {})
                zone_analytics["requests"] += sum_data.get("requests", 0)
                zone_analytics["bandwidth"] += sum_data.get("bytes", 0)
                zone_analytics["threats"] += sum_data.get("threats", 0)
                zone_analytics["page_views"] += sum_data.get("pageViews", 0)
                zone_analytics["cached_requests"] += sum_data.get("cachedRequests", 0)
                zone_analytics["cached_bandwidth"] += sum_data.get("cachedBytes", 0)

            # Performance metrics from httpRequestsAdaptiveGroups (Pro+ plans)
            # Collect all quantile values for weighted averaging
            quantile_values: dict[str, list[tuple[float, int]]] = {
                "ttfb_p50": [],
                "ttfb_p95": [],
                "ttfb_p99": [],
                "origin_response_p50": [],
                "origin_response_p95": [],
                "origin_response_p99": [],
                "edge_dns_p50": [],
                "edge_dns_p95": [],
                "edge_dns_p99": [],
            }

            for group in zone_data.get("httpRequestsAdaptiveGroups", []):
                quantiles = group.get("quantiles", {})
                count = group.get("count", 0)

                if count > 0:
                    # TTFB (Time to First Byte) - field names include Ms suffix
                    if quantiles.get("edgeTimeToFirstByteMsP50"):
                        quantile_values["ttfb_p50"].append(
                            (quantiles["edgeTimeToFirstByteMsP50"], count)
                        )
                    if quantiles.get("edgeTimeToFirstByteMsP95"):
                        quantile_values["ttfb_p95"].append(
                            (quantiles["edgeTimeToFirstByteMsP95"], count)
                        )
                    if quantiles.get("edgeTimeToFirstByteMsP99"):
                        quantile_values["ttfb_p99"].append(
                            (quantiles["edgeTimeToFirstByteMsP99"], count)
                        )
                    # Origin Response Duration
                    if quantiles.get("originResponseDurationMsP50"):
                        quantile_values["origin_response_p50"].append(
                            (quantiles["originResponseDurationMsP50"], count)
                        )
                    if quantiles.get("originResponseDurationMsP95"):
                        quantile_values["origin_response_p95"].append(
                            (quantiles["originResponseDurationMsP95"], count)
                        )
                    if quantiles.get("originResponseDurationMsP99"):
                        quantile_values["origin_response_p99"].append(
                            (quantiles["originResponseDurationMsP99"], count)
                        )
                    # Edge DNS Response Time
                    if quantiles.get("edgeDnsResponseTimeMsP50"):
                        quantile_values["edge_dns_p50"].append(
                            (quantiles["edgeDnsResponseTimeMsP50"], count)
                        )
                    if quantiles.get("edgeDnsResponseTimeMsP95"):
                        quantile_values["edge_dns_p95"].append(
                            (quantiles["edgeDnsResponseTimeMsP95"], count)
                        )
                    if quantiles.get("edgeDnsResponseTimeMsP99"):
                        quantile_values["edge_dns_p99"].append(
                            (quantiles["edgeDnsResponseTimeMsP99"], count)
                        )

            zone_analytics["ttfb_p50"] = _weighted_avg(quantile_values["ttfb_p50"])
            zone_analytics["ttfb_p95"] = _weighted_avg(quantile_values["ttfb_p95"])
            zone_analytics["ttfb_p99"] = _weighted_avg(quantile_values["ttfb_p99"])
            zone_analytics["origin_response_p50"] = _weighted_avg(
                quantile_values["origin_response_p50"]
            )
            zone_analytics["origin_response_p95"] = _weighted_avg(
                quantile_values["origin_response_p95"]
            )
            zone_analytics["origin_response_p99"] = _weighted_avg(
                quantile_values["origin_response_p99"]
            )
            zone_analytics["edge_dns_p50"] = _weighted_avg(quantile_values["edge_dns_p50"])
            zone_analytics["edge_dns_p95"] = _weighted_avg(quantile_values["edge_dns_p95"])
            zone_analytics["edge_dns_p99"] = _weighted_avg(quantile_values["edge_dns_p99"])

            return zone_analytics

        # Parallel execution for all zones
        results = parallel_map(fetch_single_zone, zone_ids, logger=self)

        # Convert results, handling None for failed fetches
        analytics: dict[str, dict[str, Any]] = {}
        for zone_key, zone_result in results.items():
            analytics[zone_key] = (
                zone_result if zone_result is not None else empty_analytics.copy()
            )

        return analytics

    def fetch_r2_analytics(
        self,
        bucket_names: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch R2 bucket analytics via GraphQL.

        Args:
            bucket_names: List of bucket names
            timeframe: Time range for analytics (ignored for storage, always uses 24h)

        Returns:
            Dictionary mapping bucket name to analytics data
        """
        if not bucket_names:
            return {}

        # Force 24h timeframe for R2 storage metrics as they are snapshots
        # and may not appear in shorter windows (like 5m or 1h)
        # Using 24h ensures we find the latest snapshot
        start_time, end_time = self._get_time_range("24h")

        query = """
        query R2Storage($accountTag: String!, $datetimeStart: Time!, $datetimeEnd: Time!) {
          viewer {
            accounts(filter: {accountTag: $accountTag}) {
              r2StorageAdaptiveGroups(
                filter: {
                  datetime_geq: $datetimeStart
                  datetime_leq: $datetimeEnd
                }
                limit: 1000
              ) {
                dimensions {
                  bucketName
                }
                max {
                  payloadSize
                  objectCount
                }
              }
            }
          }
        }
        """

        variables = {
            "accountTag": self.account_id,
            "datetimeStart": start_time,
            "datetimeEnd": end_time,
        }

        data = self._graphql_query(query, variables)
        accounts = data.get("viewer", {}).get("accounts", [])

        # Default empty analytics
        empty_analytics = {
            "storage_bytes": 0,
            "object_count": 0,
        }

        analytics: dict[str, dict[str, Any]] = {
            name: empty_analytics.copy() for name in bucket_names
        }

        if accounts:
            groups = accounts[0].get("r2StorageAdaptiveGroups", [])
            for group in groups:
                bucket_name = group.get("dimensions", {}).get("bucketName")
                if not bucket_name:
                    continue

                target_bucket = None

                # 1. Exact match
                if bucket_name in analytics:
                    target_bucket = bucket_name
                else:
                    # 2. Check for jurisdiction prefixes (e.g. "eu-bucket" or "eu_bucket")
                    # Cloudflare sometimes returns bucket names with jurisdiction prefix in analytics
                    matched_prefix = False
                    for name in analytics:
                        # Check prefixes from configured jurisdictions
                        for jurisdiction in R2_JURISDICTIONS:
                            if not jurisdiction:
                                continue
                            if bucket_name in (
                                f"{jurisdiction}-{name}",
                                f"{jurisdiction}_{name}",
                            ):
                                target_bucket = name
                                matched_prefix = True
                                break

                        if matched_prefix:
                            break

                        # Fallback: check if it ends with the name (risky if one bucket name is suffix of another)
                        # but R2 names are usually distinct enough
                        if bucket_name.endswith(f"-{name}") or bucket_name.endswith(f"_{name}"):
                            target_bucket = name
                            break

                if target_bucket:
                    max_data = group.get("max", {})
                    # Only update if values are non-zero (or if we haven't found data yet)
                    # Since we query 24h, we might get multiple groups if not grouped by bucket?
                    # The query groups by nothing explicit, but dimensions includes bucketName.
                    # It returns max payloadSize/objectCount in the period.

                    storage_bytes = float(max_data.get("payloadSize", 0))
                    object_count = float(max_data.get("objectCount", 0))

                    # Store the max values found (in case of multiple groups/snapshots)
                    current_storage = float(analytics[target_bucket].get("storage_bytes", 0))
                    current_objects = float(analytics[target_bucket].get("object_count", 0))

                    analytics[target_bucket] = {
                        "storage_bytes": max(current_storage, storage_bytes),
                        "object_count": max(current_objects, object_count),
                    }

        return analytics

    @staticmethod
    def fetch_r2_account_usage(
        bucket_analytics: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Fetch R2 account-wide usage and included free tier.

        Aggregates storage and object counts from existing per-bucket analytics.

        Args:
            bucket_analytics: Per-bucket analytics from fetch_r2_analytics()

        Returns:
            Dictionary with usage and included free tier data:
            - total_storage, max_storage
            - total_objects, total_buckets
        """
        total_storage = sum(data.get("storage_bytes", 0) for data in bucket_analytics.values())
        total_objects = sum(data.get("object_count", 0) for data in bucket_analytics.values())
        total_buckets = len(bucket_analytics)

        max_storage = R2_FREE_STORAGE

        return {
            "total_storage": total_storage,
            "max_storage": max_storage,
            "total_objects": total_objects,
            "total_buckets": total_buckets,
        }

    def fetch_dns_analytics(
        self,
        zone_ids: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch DNS analytics via GraphQL.

        Uses parallel execution for multiple zones.

        Args:
            zone_ids: List of zone IDs
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping zone ID to DNS analytics data
        """
        if not zone_ids:
            return {}

        start_time, end_time = self._get_time_range(timeframe)

        def fetch_single_zone_dns(current_zone_id: str) -> dict[str, Any]:
            """Fetch DNS analytics for a single zone."""
            query = """
            query DNSAnalytics($zoneTag: String!, $since: Time!, $until: Time!) {
              viewer {
                zones(filter: {zoneTag: $zoneTag}) {
                  dnsAnalyticsAdaptiveGroups(limit: 100, filter: {datetime_gt: $since, datetime_lt: $until}) {
                    count
                    dimensions {
                      responseCode
                    }
                  }
                }
              }
            }
            """

            variables = {
                "zoneTag": current_zone_id,
                "since": start_time,
                "until": end_time,
            }

            data = self._graphql_query(query, variables)
            zones = data.get("viewer", {}).get("zones", [])

            dns_analytics: dict[str, Any] = {
                "query_count": 0,
                "noerror_count": 0,
                "nxdomain_count": 0,
                "servfail_count": 0,
            }

            if zones:
                for group in zones[0].get("dnsAnalyticsAdaptiveGroups", []):
                    query_count = group.get("count", 0)
                    dimensions = group.get("dimensions", {})

                    dns_analytics["query_count"] += query_count

                    response_code = dimensions.get("responseCode", "").upper()
                    if response_code == "NOERROR":
                        dns_analytics["noerror_count"] += query_count
                    elif response_code == "NXDOMAIN":
                        dns_analytics["nxdomain_count"] += query_count
                    elif response_code == "SERVFAIL":
                        dns_analytics["servfail_count"] += query_count

            return dns_analytics

        # Parallel execution for all zones
        results = parallel_map(fetch_single_zone_dns, zone_ids, logger=self)

        # Convert results, handling None for failed fetches
        empty_analytics = {
            "query_count": 0,
            "noerror_count": 0,
            "nxdomain_count": 0,
            "servfail_count": 0,
        }
        analytics: dict[str, dict[str, Any]] = {}
        for zone_key, zone_result in results.items():
            analytics[zone_key] = (
                zone_result if zone_result is not None else empty_analytics.copy()
            )

        return analytics

    # =========================================================================
    # D1 Database Methods
    # =========================================================================

    def list_d1_databases(self) -> list[dict[str, Any]]:
        """List all D1 databases.

        Returns:
            List of D1 database objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/d1/database")
        return result if isinstance(result, list) else []

    def fetch_d1_analytics(
        self,
        database_ids: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch D1 database analytics via GraphQL.

        Uses parallel execution for multiple databases.

        Args:
            database_ids: List of database IDs
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping database ID to analytics data
        """
        if not database_ids:
            return {}

        start_date, end_date = self._get_date_range(timeframe)

        def fetch_single_database(current_db_id: str) -> dict[str, Any]:
            """Fetch analytics for a single D1 database."""
            query = """
            query D1Analytics($accountTag: String!, $databaseId: String!, $dateStart: Date!, $dateEnd: Date!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  d1AnalyticsAdaptiveGroups(
                    limit: 100
                    filter: {
                      databaseId: $databaseId
                      date_geq: $dateStart
                      date_leq: $dateEnd
                    }
                  ) {
                    sum {
                      rowsRead
                      rowsWritten
                      readQueries
                      writeQueries
                    }
                    avg {
                      queryBatchTimeMs
                    }
                    count
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "databaseId": current_db_id,
                "dateStart": start_date,
                "dateEnd": end_date,
            }

            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            # Default empty analytics
            db_analytics: dict[str, Any] = {
                "read_rows": 0,
                "write_rows": 0,
                "query_count": 0,
                "duration_avg": 0.0,
            }

            if accounts:
                groups = accounts[0].get("d1AnalyticsAdaptiveGroups", [])

                total_duration = 0.0
                total_groups = 0

                for group in groups:
                    sum_data = group.get("sum", {})
                    avg_data = group.get("avg", {})

                    db_analytics["read_rows"] += sum_data.get("rowsRead", 0)
                    db_analytics["write_rows"] += sum_data.get("rowsWritten", 0)

                    # queryCount is split into readQueries and writeQueries
                    read_queries = sum_data.get("readQueries", 0)
                    write_queries = sum_data.get("writeQueries", 0)
                    db_analytics["query_count"] += read_queries + write_queries

                    # Calculate weighted average for duration if available
                    # durationMs is now queryBatchTimeMs
                    duration = avg_data.get("queryBatchTimeMs", 0)
                    count = group.get("count", 0)
                    if count > 0 and duration:
                        total_duration += duration * count
                        total_groups += count

                if total_groups > 0:
                    db_analytics["duration_avg"] = total_duration / total_groups

            return db_analytics

        # Parallel execution for all databases
        results = parallel_map(fetch_single_database, database_ids, logger=self)

        # Convert results, handling None for failed fetches
        empty_db_analytics = {
            "read_rows": 0,
            "write_rows": 0,
            "query_count": 0,
            "duration_avg": 0.0,
        }
        analytics: dict[str, dict[str, Any]] = {}
        for db_key, db_result in results.items():
            analytics[db_key] = db_result if db_result is not None else empty_db_analytics.copy()

        return analytics

    def fetch_d1_daily_usage(
        self,
        databases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Fetch D1 account-wide daily usage and monitoring thresholds.

        Args:
            databases: List of D1 database objects from list_d1_databases()

        Returns:
            Dictionary with usage and limit data:
            - total_databases: Number of D1 databases
            - max_databases: Plan limit for databases
            - total_storage: Total storage in bytes (sum of file_size)
            - max_storage: Plan limit for storage in bytes
            - daily_rows_read: Rows read today (across all databases)
            - daily_rows_read_limit: Plan limit for daily rows read
            - daily_rows_written: Rows written today (across all databases)
            - daily_rows_written_limit: Plan limit for daily rows written
            - is_paid_plan: Whether account has paid plan
        """
        # Count databases and sum storage from REST API data
        total_databases = len(databases)
        total_storage = sum(db.get("file_size", 0) for db in databases)

        # Query GraphQL for today's rows read/written across ALL databases
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        query = """
        query D1DailyUsage($accountTag: String!, $date: Date!) {
          viewer {
            accounts(filter: {accountTag: $accountTag}) {
              d1AnalyticsAdaptiveGroups(
                limit: 10000
                filter: {
                  date_geq: $date
                  date_leq: $date
                }
              ) {
                sum {
                  rowsRead
                  rowsWritten
                }
              }
            }
          }
        }
        """

        variables = {
            "accountTag": self.account_id,
            "date": today,
        }

        daily_rows_read = 0
        daily_rows_written = 0

        try:
            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            if accounts:
                groups = accounts[0].get("d1AnalyticsAdaptiveGroups", [])
                for group in groups:
                    sum_data = group.get("sum", {})
                    daily_rows_read += sum_data.get("rowsRead", 0)
                    daily_rows_written += sum_data.get("rowsWritten", 0)
        except Exception as exc:
            self.log_warning(f"Could not fetch D1 daily usage: {exc}")

        # Determine plan limits
        is_paid = self.is_workers_paid_plan()

        if is_paid:
            max_databases = D1_PAID_MAX_DATABASES
            max_storage = D1_PAID_MAX_STORAGE
            rows_read_limit = D1_PAID_MONTHLY_ROWS_READ
            rows_written_limit = D1_PAID_MONTHLY_ROWS_WRITTEN
        else:
            max_databases = D1_FREE_MAX_DATABASES
            max_storage = D1_FREE_MAX_STORAGE
            rows_read_limit = D1_FREE_DAILY_ROWS_READ
            rows_written_limit = D1_FREE_DAILY_ROWS_WRITTEN

        return {
            "total_databases": total_databases,
            "max_databases": max_databases,
            "total_storage": total_storage,
            "max_storage": max_storage,
            "daily_rows_read": daily_rows_read,
            "daily_rows_read_limit": rows_read_limit,
            "daily_rows_written": daily_rows_written,
            "daily_rows_written_limit": rows_written_limit,
            "is_paid_plan": is_paid,
        }

    # =========================================================================
    # SSL/TLS Methods
    # =========================================================================

    def get_ssl_setting(self, zone_id: str) -> dict[str, Any]:
        """Get SSL mode setting for a zone.

        Args:
            zone_id: Zone ID

        Returns:
            SSL setting object with 'value' key (off/flexible/full/strict)
        """
        result = self._rest_get(f"zones/{zone_id}/settings/ssl")
        return result if isinstance(result, dict) else {}

    # =========================================================================
    # Pages Methods
    # =========================================================================

    def list_pages_projects(self) -> list[dict[str, Any]]:
        """List all Pages projects.

        Returns:
            List of Pages project objects
        """
        result = self._rest_get(f"accounts/{self.account_id}/pages/projects")
        return result if isinstance(result, list) else []

    def get_pages_deployments(self, project_name: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get deployments for a Pages project.

        Args:
            project_name: Project name
            limit: Maximum number of deployments to return (default 5)

        Returns:
            List of deployment objects sorted by created_on (newest first)
        """
        endpoint = (
            f"accounts/{self.account_id}/pages/projects/{project_name}/deployments"
            f"?per_page={limit}"
        )
        result = self._rest_get(endpoint)
        return result if isinstance(result, list) else []

    def fetch_pages_functions_analytics(
        self,
        project_names: list[str],
        timeframe: str = "24h",
    ) -> dict[str, dict[str, Any]]:
        """Fetch Pages Functions analytics via GraphQL.

        Uses parallel execution for multiple projects.

        Args:
            project_names: List of project names with Functions
            timeframe: Time range for analytics

        Returns:
            Dictionary mapping project name to analytics data
        """
        if not project_names:
            return {}

        start_time, end_time = self._get_time_range(timeframe)

        def fetch_single_project(current_project_name: str) -> dict[str, Any]:
            """Fetch Functions analytics for a single Pages project."""
            query = """
            query GetPagesFunctionsAnalytics($accountTag: String!, $datetimeStart: Time!, $datetimeEnd: Time!, $scriptName: String!) {
              viewer {
                accounts(filter: {accountTag: $accountTag}) {
                  pagesFunctionsInvocationsAdaptiveGroups(
                    limit: 1000
                    filter: {
                      scriptName: $scriptName
                      datetime_geq: $datetimeStart
                      datetime_leq: $datetimeEnd
                    }
                  ) {
                    sum {
                      requests
                      errors
                    }
                    quantiles {
                      cpuTimeP50
                      cpuTimeP99
                    }
                  }
                }
              }
            }
            """

            variables = {
                "accountTag": self.account_id,
                "datetimeStart": start_time,
                "datetimeEnd": end_time,
                "scriptName": current_project_name,
            }

            data = self._graphql_query(query, variables)
            accounts = data.get("viewer", {}).get("accounts", [])

            # Default empty analytics
            empty_project_analytics = {
                "requests": 0,
                "errors": 0,
                "cpu_time_p50": 0,
                "cpu_time_p99": 0,
            }

            if not accounts:
                return empty_project_analytics

            invocations = accounts[0].get("pagesFunctionsInvocationsAdaptiveGroups", [])
            if not invocations:
                return empty_project_analytics

            total_requests = 0
            total_errors = 0
            # Collect quantile values for weighted averaging
            quantile_values: dict[str, list[tuple[float, int]]] = {
                "cpu_time_p50": [],
                "cpu_time_p99": [],
            }

            for inv in invocations:
                sum_data = inv.get("sum", {})
                quantiles = inv.get("quantiles", {})

                request_count = sum_data.get("requests", 0)
                total_requests += request_count
                total_errors += sum_data.get("errors", 0)

                if request_count > 0:
                    if quantiles.get("cpuTimeP50"):
                        quantile_values["cpu_time_p50"].append(
                            (quantiles["cpuTimeP50"], request_count)
                        )
                    if quantiles.get("cpuTimeP99"):
                        quantile_values["cpu_time_p99"].append(
                            (quantiles["cpuTimeP99"], request_count)
                        )

            return {
                "requests": total_requests,
                "errors": total_errors,
                # CPU Time in microseconds from API, convert to ms
                "cpu_time_p50": _weighted_avg(quantile_values["cpu_time_p50"], to_ms=True),
                "cpu_time_p99": _weighted_avg(quantile_values["cpu_time_p99"], to_ms=True),
            }

        # Parallel execution for all projects
        results = parallel_map(fetch_single_project, project_names, logger=self)

        # Convert results, handling None for failed fetches
        empty_pages_analytics = {
            "requests": 0,
            "errors": 0,
            "cpu_time_p50": 0,
            "cpu_time_p99": 0,
        }
        analytics: dict[str, dict[str, Any]] = {}
        for project_key, project_result in results.items():
            analytics[project_key] = (
                project_result if project_result is not None else empty_pages_analytics.copy()
            )

        return analytics
