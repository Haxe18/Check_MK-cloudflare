#!/usr/bin/env python3
"""Type definitions for Cloudflare monitoring."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricDefinition:
    """Definition of a Cloudflare metric to fetch."""

    name: str  # e.g., "requests", "errors"
    stat: str  # e.g., "sum", "avg", "p50", "p99"
    unit: str  # e.g., "Count", "Bytes", "Milliseconds", "Percent"

    def __hash__(self) -> int:
        """Return a stable hash for set/dict usage.

        Returns:
            int: Hash of metric definition fields.
        """
        return hash((self.name, self.stat, self.unit))


@dataclass
class Resource:
    """A discovered Cloudflare resource."""

    id: str  # Resource identifier  # pylint: disable=invalid-name
    name: str = ""  # Human-readable name
    resource_type: str = ""  # e.g., "worker", "kv_namespace", "zone"
    metadata: dict[str, Any] = field(default_factory=dict)
    available_metrics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert resource to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "resource_type": self.resource_type,
            "metadata": self.metadata,
            "available_metrics": self.available_metrics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resource":
        """Create Resource from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            resource_type=data.get("resource_type", ""),
            metadata=data.get("metadata", {}),
            available_metrics=data.get("available_metrics", []),
        )


@dataclass
class MetricResult:
    """Result of fetching a single metric."""

    resource_id: str
    metric_name: str
    value: float
    unit: str
    stat: str
    timestamp: str | None = None
    timeframe: str = "24h"  # e.g., "5m", "15m", "1h", "6h", "24h"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metric result to dictionary for serialization."""
        return {
            "resource_id": self.resource_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "stat": self.stat,
            "timestamp": self.timestamp,
            "timeframe": self.timeframe,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetricResult":
        """Create MetricResult from dictionary."""
        return cls(
            resource_id=data.get("resource_id", ""),
            metric_name=data.get("metric_name", ""),
            value=data.get("value", 0.0),
            unit=data.get("unit", ""),
            stat=data.get("stat", ""),
            timestamp=data.get("timestamp"),
            timeframe=data.get("timeframe", "24h"),
            metadata=data.get("metadata", {}),
        )


def create_metric(
    resource: Resource,
    metric_name: str,
    value: float,
    unit: str,
    stat: str,
    timeframe: str,
    extra_metadata: dict[str, Any] | None = None,
) -> MetricResult:
    """Create a MetricResult with common defaults.

    Args:
        resource: The resource this metric belongs to
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement (Count, Bytes, etc.)
        stat: Statistic type (sum, avg, gauge, etc.)
        timeframe: Time range for the metric
        extra_metadata: Additional metadata to include

    Returns:
        MetricResult with resource name in metadata
    """
    metadata = {"name": resource.name}
    # Include plan info if available (for Pro+ feature detection)
    if "plan" in resource.metadata:
        metadata["plan"] = resource.metadata["plan"]
    if extra_metadata:
        metadata.update(extra_metadata)

    return MetricResult(
        resource_id=resource.id,
        metric_name=metric_name,
        value=value,
        unit=unit,
        stat=stat,
        timeframe=timeframe,
        metadata=metadata,
    )
