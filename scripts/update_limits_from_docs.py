#!/usr/bin/env python3
"""Refresh Cloudflare limit constants from docs markdown sources.

Uses Gemini Flash to extract limit values from Cloudflare documentation
discovered via each product's llms.txt. All limit constants and doc URLs are discovered
dynamically — adding a new FREE-tier constant to constants.py is enough.

Usage:
  GEMINI_API_KEY=... python scripts/update_limits_from_docs.py --check
  GEMINI_API_KEY=... python scripts/update_limits_from_docs.py --write
  GEMINI_API_KEY=... python scripts/update_limits_from_docs.py --check --debug

Exit codes:
  0  success (stdout is JSON with changed/changelog fields)
  1  error
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSTANTS_PATH = REPO_ROOT / "cloudflare/lib/constants.py"
# The root llms.txt only links to one llms.txt per product; the pricing and
# limits pages are listed there.
PRODUCT_LLMS_URL = "https://developers.cloudflare.com/{service}/llms.txt"
GEMINI_MODEL = "gemini-3.8-flash"


def discover_limit_constants(constants_text: str) -> tuple[dict[str, int], set[str]]:
    """Discover FREE-tier limit constants and byte-valued keys from constants.py.

    Scans for lines matching ``SOME_FREE_CONSTANT = <expr>`` and evaluates
    the expression to get the integer value.

    Args:
        constants_text: Full contents of ``constants.py``.

    Returns:
        Tuple of ``(keys, byte_keys)`` where *keys* maps constant names to
        their current integer values and *byte_keys* contains names whose
        values are expressed in bytes (``* 1024 * 1024 * 1024``).
    """
    keys: dict[str, int] = {}
    byte_keys: set[str] = set()

    for match in re.finditer(
        r"^([A-Z][A-Z0-9_]*FREE[A-Z0-9_]*)\s*=\s*([^#\n]+)",
        constants_text,
        re.MULTILINE,
    ):
        key, expr = match.group(1), match.group(2).strip()
        try:
            keys[key] = int(eval(expr))  # nosec: handles "5 * 1024 * 1024 * 1024"
        except Exception:
            continue
        if "1024 * 1024 * 1024" in expr:
            byte_keys.add(key)

    return keys, byte_keys


def _services_from_constants(keys: dict[str, int]) -> set[str]:
    """Derive service names from constant prefixes.

    Example: ``D1_FREE_MAX_DATABASES`` → ``d1``, ``KV_FREE_DAILY_READS`` → ``kv``.

    Args:
        keys: Constant names as returned by :func:`discover_limit_constants`.

    Returns:
        Set of lowercase service names (e.g. ``{"d1", "kv", "r2"}``).
    """
    services = set()
    for key in keys:
        prefix = key.split("_FREE")[0].lower()
        services.add(prefix)
    return services


def discover_doc_urls(llms_text: str, needed_services: set[str]) -> dict[str, str]:
    """Find pricing and limits doc URLs from llms.txt for the given services.

    Extracts all HTTP(S) URLs, keeps only those containing ``/pricing`` or
    ``/limits``, and filters by service name (first path segment).  The first
    URL found per service+type wins to avoid overwrites by sub-path variants.

    Args:
        llms_text: Raw contents of a Cloudflare product's ``llms.txt``.
        needed_services: Service names to look for (e.g. ``{"d1", "kv"}``).

    Returns:
        Dict mapping ``"{service}_{pricing|limits}"`` to the doc URL.
    """
    urls = re.findall(r"https?://[^\s)\]>]+", llms_text)
    docs: dict[str, str] = {}
    for url in urls:
        if "/pricing" not in url and "/limits" not in url:
            continue
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        if not parts:
            continue
        service = parts[0]
        if service not in needed_services:
            continue
        doc_type = "pricing" if "/pricing" in url else "limits"
        key = f"{service}_{doc_type}"
        if key not in docs:
            docs[key] = url
    return docs


def fetch_url(url: str) -> str:
    """Fetch a URL and return its content as text.

    Args:
        url: The URL to fetch.

    Returns:
        Response body decoded as UTF-8.
    """
    req = Request(
        url,
        headers={
            "User-Agent": "https://github.com/Haxe18/Check_MK-cloudflare Cloudflare Limits Scraper"
        },
    )
    with urlopen(req, timeout=30) as resp:  # nosec: B310 - trusted docs endpoint
        return resp.read().decode("utf-8", errors="ignore")


def extract_limits_via_llm(
    raw_docs: dict[str, str],
    existing_keys: dict[str, int],
    byte_keys: set[str],
) -> dict[str, int]:
    """Send raw markdown docs to Gemini Flash and extract limit values.

    Args:
        raw_docs: Mapping of doc name to raw markdown content.
        existing_keys: Current constant names and their integer values.
        byte_keys: Subset of keys whose values are in bytes.

    Returns:
        Dict mapping each constant name to its extracted integer value.

    Raises:
        ValueError: If the LLM response is missing keys or contains
            invalid (non-positive / non-integer) values.
    """
    # Gemini answers 503 "high demand" for minutes at a time. The SDK default
    # gives up after ~15 s; this keeps retrying for ~4 minutes. Without a timeout
    # a request that never gets an answer hangs forever; timeouts are retried too.
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=HttpOptions(
            timeout=180_000,  # ms per request
            retry_options=HttpRetryOptions(attempts=8, initial_delay=2, max_delay=120),
        ),
    )

    docs_text = "\n\n".join(f"=== {name} ===\n{content}" for name, content in raw_docs.items())

    keys_list = sorted(existing_keys.keys())
    keys_description = "\n".join(f"- {k} (current: {existing_keys[k]:_})" for k in keys_list)

    byte_keys_hint = ""
    if byte_keys:
        byte_keys_hint = (
            "\n\nStorage keys (return value in bytes, 1 GB = 1073741824 bytes / binary GiB):\n"
            + "\n".join(f"- {k}" for k in sorted(byte_keys))
        )

    prompt = f"""\
Extract Cloudflare FREE plan limits from the documentation below.
Return a JSON object with exactly these keys and integer values:

{keys_description}
{byte_keys_hint}

Rules:
- Storage values listed above MUST be in bytes.
- All other values are plain counts (requests, rows, operations, databases).
- All values must be positive integers.
- Use only values explicitly stated for the FREE plan / Workers Free plan.

Documentation:

{docs_text}"""

    log.debug("LLM prompt (%d chars):\n%.500s...", len(prompt), prompt)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    log.debug("LLM response: %s", response.text)

    limits = json.loads(response.text)

    missing = set(keys_list) - set(limits.keys())
    if missing:
        raise ValueError(f"LLM response missing keys: {', '.join(sorted(missing))}")

    for key in keys_list:
        val = limits[key]
        if not isinstance(val, int) or val <= 0:
            raise ValueError(f"Invalid value for {key}: {val!r} (expected positive int)")

    return {k: limits[k] for k in keys_list}


def format_int_underscored(value: int) -> str:
    """Format an integer with underscore grouping (e.g. ``1_000_000``).

    Args:
        value: The integer to format.

    Returns:
        Underscore-grouped string representation.
    """
    return f"{value:_}"


def render_constant_value(key: str, value: int, byte_keys: set[str]) -> str:
    """Render a constant value as a Python literal for constants.py.

    Byte-valued keys that are exact GiB multiples are rendered as
    ``N * 1024 * 1024 * 1024``; all others use underscore grouping.

    Args:
        key: Constant name.
        value: Integer value.
        byte_keys: Set of keys whose values are in bytes.

    Returns:
        Python literal string suitable for ``constants.py``.
    """
    if key in byte_keys and value % (1024 * 1024 * 1024) == 0:
        gb = value // (1024 * 1024 * 1024)
        return f"{gb} * 1024 * 1024 * 1024"
    return format_int_underscored(value)


def update_constants_content(original: str, limits: dict[str, int], byte_keys: set[str]) -> str:
    """Replace constant values in constants.py source text.

    Args:
        original: Full contents of ``constants.py``.
        limits: Mapping of constant name to new integer value.
        byte_keys: Set of keys whose values are in bytes.

    Returns:
        Updated ``constants.py`` contents.

    Raises:
        ValueError: If a constant name is not found in the source text.
    """
    updated = original
    for key, value in limits.items():
        value_literal = render_constant_value(key, value, byte_keys)
        pattern = re.compile(
            rf"^(?P<prefix>{re.escape(key)}\s*=\s*)(?P<value>[^#\n]+)(?P<suffix>.*)$",
            re.MULTILINE,
        )

        def repl(match: re.Match[str]) -> str:
            suffix = match.group("suffix")
            if suffix.startswith("#"):
                suffix = "  " + suffix
            return f"{match.group('prefix')}{value_literal}{suffix}"

        updated, n = pattern.subn(repl, updated, count=1)
        if n == 0:
            raise ValueError(f"Constant not found in constants file: {key}")
    return updated


def build_changelog(old: dict[str, int], new: dict[str, int]) -> str:
    """Build a markdown table of changed values for the PR body.

    Args:
        old: Previous constant values.
        new: Updated constant values.

    Returns:
        Markdown string with a table of changes, or a "no changes" message.
    """
    changes = [(k, old.get(k, 0), new[k]) for k in sorted(new) if old.get(k, 0) != new[k]]
    if not changes:
        return "No changes detected."
    lines = [
        "## Changed Limits",
        "",
        "| Constant | Old | New |",
        "|---|---|---|",
    ]
    for key, old_val, new_val in changes:
        lines.append(f"| `{key}` | `{old_val:_}` | `{new_val:_}` |")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (without ``sys.argv[0]``).

    Returns:
        Exit code: 0 (success), 1 (error).  Stdout is always JSON with
        ``changed`` and ``changelog`` fields.
    """
    parser = argparse.ArgumentParser(description="Refresh Cloudflare limits from docs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Dry-run, do not write changes")
    group.add_argument("--write", action="store_true", help="Write changes to constants.py")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    if not os.environ.get("GEMINI_API_KEY"):
        log.error("GEMINI_API_KEY environment variable is required")
        return 1

    try:
        constants_text = CONSTANTS_PATH.read_text(encoding="utf-8")
        existing_keys, byte_keys = discover_limit_constants(constants_text)
        log.debug("Discovered %d limit constants from constants.py", len(existing_keys))
        log.debug("Keys: %s", sorted(existing_keys.keys()))
        log.debug("Byte keys: %s", sorted(byte_keys))

        needed_services = _services_from_constants(existing_keys)
        log.debug("Needed services: %s", sorted(needed_services))

        doc_urls: dict[str, str] = {}
        for service in sorted(needed_services):
            llms_text = fetch_url(PRODUCT_LLMS_URL.format(service=service))
            service_urls = discover_doc_urls(llms_text, {service})
            if not service_urls:
                raise ValueError(f"No pricing/limits doc URLs found for {service}")
            doc_urls.update(service_urls)
        log.debug("Found %d pricing/limits doc URLs", len(doc_urls))
        log.debug("Doc URLs: %s", json.dumps(doc_urls, indent=2))

        raw_docs: dict[str, str] = {}
        for name, url in doc_urls.items():
            log.debug("Fetching %s ...", name)
            raw_docs[name] = fetch_url(url)

        limits = extract_limits_via_llm(raw_docs, existing_keys, byte_keys)
        log.debug("LLM returned values: %s", json.dumps(limits, indent=2))
    except (URLError, TimeoutError, ValueError) as exc:
        log.error("Failed to fetch or parse docs: %s", exc)
        return 1

    constants_before = constants_text
    constants_after = update_constants_content(constants_before, limits, byte_keys)
    changed = constants_before != constants_after

    if args.write and changed:
        CONSTANTS_PATH.write_text(constants_after, encoding="utf-8")

    changelog = build_changelog(existing_keys, limits) if changed else ""

    result: dict[str, object] = {
        "changed": changed,
        "changelog": changelog,
        "sources": doc_urls,
        "limits": limits,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
