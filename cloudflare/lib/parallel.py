#!/usr/bin/env python3
"""Parallel execution utilities for Cloudflare API calls."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, TypeVar

from .constants import DEFAULT_MAX_WORKERS
from .logger import LoggerMixin

T = TypeVar("T")
R = TypeVar("R")


def parallel_map(
    func: Callable[[T], R],
    items: list[T],
    max_workers: int = DEFAULT_MAX_WORKERS,
    logger: LoggerMixin | None = None,
) -> dict[T, R]:
    """Execute func for each item in parallel, return {item: result}.

    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of concurrent workers (default: 8)
        logger: Optional logger for error reporting

    Returns:
        Dictionary mapping each item to its result.
        Items that raised exceptions will have None as their result.
    """
    results: dict[T, R] = {}

    if not items:
        return results

    # Limit workers to item count and max
    workers = min(max_workers, len(items))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_item = {executor.submit(func, item): item for item in items}

        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                results[item] = future.result()
            except Exception as exc:
                # Log error, set None for failed item
                if logger:
                    logger.log_warning(f"Parallel task failed for {item}: {exc}")
                results[item] = None  # type: ignore

    return results
