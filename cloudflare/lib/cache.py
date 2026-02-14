#!/usr/bin/env python3
"""Caching utilities for Cloudflare monitoring."""

import fcntl
import json
import threading
import time
from pathlib import Path
from typing import Any

from cmk.utils.paths import tmp_dir

from .logger import LoggerMixin


class DataCache(LoggerMixin):
    """File-based cache with TTL and file locking.

    Inherits:
        LoggerMixin: Provides logging helpers for cache diagnostics.
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl: int,
        prefix: str = "",
    ) -> None:
        """Initialize cache.

        Args:
            cache_dir: Directory for cache files
            ttl: Time-to-live in seconds
            prefix: Prefix for cache keys
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.prefix = prefix

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get full path for cache file."""
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{self.prefix}_{safe_key}.json"

    def load(self, key: str, config_key: str | None = None) -> Any:
        """Load data from cache if valid.

        Args:
            key: Cache key
            config_key: Optional config key for validation (invalidates cache if changed)

        Returns:
            Cached data or None if expired/missing/config changed
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as file_handle:
                # Acquire shared lock for reading
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(file_handle)
                finally:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

            # Check TTL
            cached_at = data.get("_cached_at", 0)
            age = time.time() - cached_at

            if age > self.ttl:
                self.log_debug(f"Cache expired for key {key} (age: {age:.0f}s, ttl: {self.ttl}s)")
                return None

            # Check config key - invalidate if configuration changed
            if config_key is not None:
                cached_config_key = data.get("_config_key")
                if cached_config_key != config_key:
                    self.log_debug(f"Cache invalidated for key {key} (config changed)")
                    return None

            self.log_debug(f"Cache hit for key {key} (age: {age:.0f}s)")
            return data.get("_data")

        except (OSError, json.JSONDecodeError) as exc:
            self.log_warning(f"Failed to load cache for key {key}: {exc}")
            return None

    def save(self, key: str, data: Any, config_key: str | None = None) -> None:
        """Save data to cache.

        Args:
            key: Cache key
            data: Data to cache
            config_key: Optional config key for later validation
        """
        cache_path = self._get_cache_path(key)

        cache_data: dict[str, Any] = {
            "_cached_at": time.time(),
            "_data": data,
        }
        if config_key is not None:
            cache_data["_config_key"] = config_key

        try:
            with open(cache_path, "w", encoding="utf-8") as file_handle:
                # Acquire exclusive lock for writing
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(cache_data, file_handle)
                finally:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

            self.log_debug(f"Cache saved for key {key}")

        except OSError as exc:
            self.log_warning(f"Failed to save cache for key {key}: {exc}")

    def delete(self, key: str) -> None:
        """Delete cache file.

        Args:
            key: Cache key
        """
        cache_path = self._get_cache_path(key)

        try:
            if cache_path.exists():
                cache_path.unlink()
                self.log_debug(f"Cache deleted for key {key}")
        except OSError as exc:
            self.log_warning(f"Failed to delete cache for key {key}: {exc}")

    def clear_all(self) -> None:
        """Clear all cache files with this prefix."""
        try:
            for cache_file in self.cache_dir.glob(f"{self.prefix}_*.json"):
                cache_file.unlink()
            self.log_info(f"Cleared all cache files with prefix {self.prefix}")
        except OSError as exc:
            self.log_warning(f"Failed to clear cache: {exc}")


class APICounter(LoggerMixin):
    """Counter for tracking API requests.

    Thread-safe: Uses a lock to protect counter access for parallel API calls.
    """

    # Cloudflare rate limits (requests per 5 minutes)
    RATE_LIMITS = {
        "default": 1200,  # REST API
        "graphql": 300,  # GraphQL API
    }

    def __init__(self) -> None:
        """Initialize API counter."""
        self._counts: dict[str, int] = {
            "default": 0,
            "graphql": 0,
        }
        self._start_time = time.time()
        self._lock = threading.Lock()

    def increment(self, count: int = 1, endpoint_type: str = "default") -> None:
        """Increment API request counter.

        Thread-safe.

        Args:
            count: Number of requests to add
            endpoint_type: Type of endpoint ("default" or "graphql")
        """
        with self._lock:
            if endpoint_type not in self._counts:
                endpoint_type = "default"
            self._counts[endpoint_type] += count

    def get_count(self, endpoint_type: str | None = None) -> int:
        """Get current request count.

        Thread-safe.

        Args:
            endpoint_type: Specific endpoint type or None for total

        Returns:
            Request count
        """
        with self._lock:
            if endpoint_type is None:
                return sum(self._counts.values())
            return self._counts.get(endpoint_type, 0)

    def get_all_counts(self) -> dict[str, int]:
        """Get all endpoint counts.

        Thread-safe.

        Returns:
            Dictionary of counts by endpoint type
        """
        with self._lock:
            return dict(self._counts)

    def get_usage_percentage(self, endpoint_type: str = "default") -> float:
        """Get usage as percentage of rate limit.

        Thread-safe.

        Args:
            endpoint_type: Type of endpoint

        Returns:
            Usage percentage (0-100+)
        """
        with self._lock:
            limit = self.RATE_LIMITS.get(endpoint_type, self.RATE_LIMITS["default"])
            count = self._counts.get(endpoint_type, 0)
            return (count / limit) * 100 if limit > 0 else 0.0

    def get_elapsed_time(self) -> float:
        """Get elapsed time since counter started.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self._start_time

    def to_dict(self) -> dict[str, Any]:
        """Convert counter to dictionary for reporting.

        Thread-safe.

        Returns:
            Dictionary with counter data
        """
        with self._lock:
            return {
                "requests_made": sum(self._counts.values()),
                "requests_by_type": dict(self._counts),
                "elapsed_seconds": self.get_elapsed_time(),
                "rate_limits": self.RATE_LIMITS,
            }


def get_cache_dir(account_id: str) -> Path:
    """Get cache directory for an account.

    Args:
        account_id: Cloudflare account ID

    Returns:
        Path to cache directory
    """
    return Path(tmp_dir) / "agents" / "agent_cloudflare" / f"cloudflare_{account_id}"
