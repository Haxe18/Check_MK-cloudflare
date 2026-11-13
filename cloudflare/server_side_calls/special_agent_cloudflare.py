#!/usr/bin/env python3
"""Server side calls for Cloudflare special agent."""

import json
from collections.abc import Iterator
from typing import Any

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)

from ..lib.constants import DEFAULT_SERVICES, DEFAULT_TIMEFRAME, WATO_TIMEFRAME_MAP


def _agent_arguments(
    params: dict[str, Any],
    _host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    """Generate command line arguments for the Cloudflare special agent.

    Args:
        params: Configuration parameters from WATO
        host_config: Host configuration

    Yields:
        SpecialAgentCommand with arguments
    """
    args: list[str | Secret] = []

    # API Token (required)
    api_token = params.get("api_token")
    if not api_token:
        return

    # Passed as a password store reference, so the token is not in the process list
    args.extend(["--api-token-reference", api_token])

    # Account ID (required)
    account_id = params.get("account_id")
    if not account_id:
        return

    args.extend(["--account-id", account_id])

    # Services to monitor
    services = params.get("services", DEFAULT_SERVICES)
    if services:
        args.extend(["--services", json.dumps(services)])

    # Cache TTL
    cache_ttl = params.get("cache_ttl")
    if cache_ttl is not None:
        args.extend(["--cache-ttl", str(cache_ttl)])

    # Discovery TTL
    discovery_ttl = params.get("discovery_ttl")
    if discovery_ttl is not None:
        args.extend(["--discovery-ttl", str(discovery_ttl)])

    # Analytics timeframe - convert from WATO format (t24h) to agent format (24h)
    timeframe_key = params.get("analytics_timeframe", "t24h")
    timeframe = WATO_TIMEFRAME_MAP.get(timeframe_key, DEFAULT_TIMEFRAME)
    args.extend(["--timeframe", timeframe])

    yield SpecialAgentCommand(command_arguments=args)


# CMK needed definition
special_agent_cloudflare = SpecialAgentConfig(
    name="cloudflare",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
