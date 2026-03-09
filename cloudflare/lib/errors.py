#!/usr/bin/env python3
"""Error collection and categorization for Cloudflare plugin."""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class CloudflareError:
    """A structured error from the Cloudflare API.

    Attributes:
        category: Error category ("api", "discovery", "metrics", "cache")
        service: Service name ("workers", "kv", "zones", etc.) or "unknown"
        message: Human-readable error message
        timestamp: Unix timestamp when error occurred
        transient: True if the error is likely to go away on its own
            (HTTP 5xx, rate limit, timeout, network error, invalid JSON response)
    """

    category: str
    service: str
    message: str
    timestamp: float = field(default_factory=time.time)
    transient: bool = False

    def to_dict(self) -> dict[str, str | float]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with category, service, message, timestamp, transient
        """
        return {
            "category": self.category,
            "service": self.service,
            "message": self.message,
            "timestamp": self.timestamp,
            "transient": self.transient,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | float]) -> "CloudflareError":
        """Create from dictionary.

        Args:
            data: Dictionary with error data

        Returns:
            CloudflareError instance
        """
        return cls(
            category=str(data.get("category", "unknown")),
            service=str(data.get("service", "unknown")),
            message=str(data.get("message", "")),
            timestamp=float(data.get("timestamp", time.time())),
            transient=bool(data.get("transient", False)),
        )


class ErrorCollector:
    """Collects and categorizes errors during Cloudflare API operations.

    This class provides structured error collection similar to the AWS
    CloudWatch plugin, allowing errors to be categorized and summarized
    for display in Check_MK.

    Thread-safe: Uses a lock to protect error list access for parallel API calls.

    Example usage:
        collector = ErrorCollector()
        collector.add("api", "workers", "Permission denied: workers/scripts")
        collector.add("api", "kv", "Rate limit exceeded")

        if collector.has_errors():
            print(f"Found {collector.count()} errors: {collector.summary()}")
            # Output: "Found 2 errors: 2 api"
    """

    def __init__(self) -> None:
        """Initialize empty error collector."""
        self._errors: list[CloudflareError] = []
        self._lock = threading.Lock()

    def add(self, category: str, service: str, message: str, transient: bool = False) -> None:
        """Add an error to the collection.

        Thread-safe: Uses lock to protect error list.

        Args:
            category: Error category ("api", "discovery", "metrics", "cache")
            service: Service name ("workers", "kv", "zones", etc.)
            message: Human-readable error message
            transient: True if the error is likely to go away on its own
        """
        error = CloudflareError(
            category=category,
            service=service,
            message=message,
            timestamp=time.time(),
            transient=transient,
        )
        with self._lock:
            self._errors.append(error)

    def has_errors(self) -> bool:
        """Check if any errors have been collected.

        Thread-safe.

        Returns:
            True if at least one error exists
        """
        with self._lock:
            return len(self._errors) > 0

    def count(self) -> int:
        """Get total number of errors.

        Thread-safe.

        Returns:
            Number of errors collected
        """
        with self._lock:
            return len(self._errors)

    def to_list(self) -> list[dict[str, str | float]]:
        """Convert all errors to list of dictionaries.

        Thread-safe.

        Returns:
            List of error dictionaries for JSON serialization
        """
        with self._lock:
            return [e.to_dict() for e in self._errors]

    def get_and_clear(self) -> list[dict[str, str | float]]:
        """Return all errors as list of dicts and clear the collection.

        Thread-safe.

        Returns:
            List of error dictionaries
        """
        with self._lock:
            errors = [e.to_dict() for e in self._errors]
            self._errors.clear()
            return errors

    def summary(self) -> str:
        """Get summary of errors by category.

        Thread-safe.

        Returns:
            Summary string like "2 api, 1 discovery"
        """
        with self._lock:
            if not self._errors:
                return "no errors"

            by_category: dict[str, int] = defaultdict(int)
            for error in self._errors:
                by_category[error.category] += 1

            parts = [f"{count} {cat}" for cat, count in sorted(by_category.items())]
            return ", ".join(parts)

    def brief(self, max_items: int = 3) -> str:
        """Get brief list of affected services.

        Thread-safe.

        Args:
            max_items: Maximum number of services to list

        Returns:
            Brief string like "workers, kv, ..." or "workers, kv"
        """
        with self._lock:
            if not self._errors:
                return ""

            # Collect unique services (preserve order of first occurrence)
            services: list[str] = []
            seen: set[str] = set()
            for error in self._errors:
                if error.service not in seen and error.service != "unknown":
                    services.append(error.service)
                    seen.add(error.service)

            if len(services) <= max_items:
                return ", ".join(services)
            return ", ".join(services[:max_items]) + ", ..."

    def by_category(self) -> dict[str, list[CloudflareError]]:
        """Group errors by category.

        Thread-safe.

        Returns:
            Dictionary mapping category to list of errors
        """
        with self._lock:
            result: dict[str, list[CloudflareError]] = defaultdict(list)
            for error in self._errors:
                result[error.category].append(error)
            return dict(result)

    def by_service(self) -> dict[str, list[CloudflareError]]:
        """Group errors by service.

        Thread-safe.

        Returns:
            Dictionary mapping service to list of errors
        """
        with self._lock:
            result: dict[str, list[CloudflareError]] = defaultdict(list)
            for error in self._errors:
                result[error.service].append(error)
            return dict(result)
