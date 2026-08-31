from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import ipaddress
import json
import socket
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import AdapterKind, FetchMode, build_policy_registry, load_source_catalog


USER_AGENT = "Ziras-POC/0.1 (+https://github.com/ksazid/ziras)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=[item.value for item in SourcePolicyScope], default="research")
    parser.add_argument("--source", action="append", default=[])
    args = parser.parse_args()

    scope = SourcePolicyScope(args.scope)
    entries = load_source_catalog()
    registry = build_policy_registry(entries)
    selected = set(args.source)
    results: list[dict[str, object]] = []

    for entry in entries:
        if selected and entry.source_key not in selected:
            continue
        if entry.fetch_mode is not FetchMode.STATIC:
            results.append(_result(entry.source_key, "skipped", reason=f"fetch_mode={entry.fetch_mode.value}"))
            continue
        if entry.policy.mode is not SourceAccessMode.ALLOW:
            results.append(_result(entry.source_key, "blocked", reason=entry.policy.reason))
            continue

        for url in entry.start_urls:
            decision = registry.decide(entry.source_key, scope=scope, source_url=url)
            if not decision.allowed:
                results.append(_result(entry.source_key, "blocked", url=url, reason=decision.reason))
                continue
            try:
                results.append(_fetch(entry.source_key, entry.adapter_kind, url, entry.policy.robots_required))
            except Exception as exc:
                results.append(_result(entry.source_key, "error", url=url, reason=type(exc).__name__))

    print(json.dumps(results, indent=2, sort_keys=True))
    return 1 if any(item["status"] == "error" for item in results) else 0


def _fetch(source_key: str, adapter_kind: AdapterKind, url: str, robots_required: bool) -> dict[str, object]:
    _assert_public_host(url)
    if robots_required and not _robots_allows(url):
        return _result(source_key, "blocked", url=url, reason="robots_disallow_or_unavailable")

    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=20) as response:
        final_url = response.geturl()
        if urlsplit(final_url).hostname != urlsplit(url).hostname:
            raise RuntimeError("cross-host redirect rejected")
        body = response.read(2_000_000)
        status = getattr(response, "status", 200)

    html = body.decode("utf-8", errors="replace")
    adapter = PublicWebSignalAdapter(TextSignalConfig(event_mode=adapter_kind is AdapterKind.EVENT))
    normalized = adapter.extract(
        source_key=source_key,
        source_url=url,
        html=html,
        observed_at=datetime.now(timezone.utc),
        content_hash=sha256(body).hexdigest(),
    )
    return _result(
        source_key,
        "ok",
        url=url,
        http_status=status,
        bytes=len(body),
        discovery_candidates=len(normalized.discoveries),
        content_hash=normalized.observation.content_hash,
    )


def _robots_allows(url: str) -> bool:
    split = urlsplit(url)
    robots_url = urljoin(f"{split.scheme}://{split.netloc}", "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        return False
    return parser.can_fetch(USER_AGENT, url)


def _assert_public_host(url: str) -> None:
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("URL has no host")
    for item in socket.getaddrinfo(host, None):
        address = ipaddress.ip_address(item[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise RuntimeError("non-public destination rejected")


def _result(source_key: str, status: str, **values: object) -> dict[str, object]:
    return {"source_key": source_key, "status": status, **values}


if __name__ == "__main__":
    raise SystemExit(main())
