from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import re
from typing import Iterable
from urllib.parse import urlsplit
from uuid import uuid4

import trafilatura

from ..domain import Discovery, DiscoveryType, FreshnessState, SourceObservation
from ..extraction import parse_discovery_date
from ..ports import SourceAdapterResult
from .structured_html import StructuredHtmlAdapter


_MONEY_RE = re.compile(r"(?:(?:€|EUR)\s*)?(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:€|EUR)?", re.IGNORECASE)
_PERCENT_RE = re.compile(r"\b(\d{1,2})\s*%\s*(?:off)?\b", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(
    r"(?P<start_day>\d{1,2})[./](?P<start_month>\d{1,2})(?:[./](?P<start_year>\d{4}))?\s*[-–]\s*"
    r"(?P<end_day>\d{1,2})[./](?P<end_month>\d{1,2})(?:[./](?P<end_year>\d{4}))?"
)
_NUMERIC_DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})[./](?P<month>\d{1,2})(?:[./](?P<year>\d{4}))?\b"
)
_EVENT_DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+\d{1,2})?(?:,?\s+\d{4})?\b",
    re.IGNORECASE,
)
_QUALITATIVE_OFFER_RE = re.compile(
    r"\b(?:offer|offers|deal|loyalty scheme|combo|skip the queue)\b",
    re.IGNORECASE,
)
_IGNORED_TITLE_LINES = {
    "more info",
    "book tickets",
    "buy tickets",
    "browse events",
    "clear filters",
    "what's on",
    "what’s on",
}


@dataclass(frozen=True, slots=True)
class TextSignalConfig:
    event_mode: bool = False
    maximum_discoveries: int = 100


class PublicWebSignalAdapter:
    """Deterministic public-page normalizer used after policy-approved acquisition."""

    name = "public-web-signal-v2"

    def __init__(self, config: TextSignalConfig | None = None) -> None:
        self.config = config or TextSignalConfig()
        self._structured = StructuredHtmlAdapter()

    def extract(
        self,
        *,
        source_key: str,
        source_url: str,
        html: str,
        observed_at: datetime,
        content_hash: str | None = None,
    ) -> SourceAdapterResult:
        digest = content_hash or sha256(html.encode("utf-8", errors="ignore")).hexdigest()
        structured = self._structured.extract(
            source_key=source_key,
            source_url=source_url,
            html=html,
            observed_at=observed_at,
            content_hash=digest,
        )
        if structured.discoveries:
            return structured

        text = trafilatura.extract(
            html,
            include_comments=False,
            include_links=False,
            include_images=False,
            favor_recall=True,
        ) or ""
        lines = tuple(_clean_lines(text.splitlines()))
        discoveries = self._discoveries(lines, source_key, source_url, observed_at)
        extraction_mode = "main_text"

        if not discoveries:
            fallback_text = trafilatura.html2txt(html) or ""
            fallback_lines = tuple(_clean_lines(fallback_text.splitlines()))
            if fallback_lines and fallback_lines != lines:
                lines = fallback_lines
                discoveries = self._discoveries(lines, source_key, source_url, observed_at)
                extraction_mode = "html2txt_fallback"

        observation = SourceObservation(
            id=uuid4(),
            source_key=source_key,
            source_url=source_url,
            observed_at=observed_at,
            content_hash=digest,
            extracted={
                "text_line_count": len(lines),
                "candidate_count": len(discoveries),
                "mode": "event" if self.config.event_mode else "promotion",
                "extraction_mode": extraction_mode,
            },
            adapter=self.name,
        )
        return SourceAdapterResult(
            observation=observation,
            discoveries=tuple(discoveries[: self.config.maximum_discoveries]),
        )

    def _discoveries(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        if self.config.event_mode:
            result = self._event_discoveries(lines, source_key, source_url, observed_at)
            if not result and _is_current_listing_url(source_url):
                result = self._current_listing_events(lines, source_key, source_url, observed_at)
            return result

        result = self._promotion_discoveries(lines, source_key, source_url, observed_at)
        if not result and _is_offer_listing_url(source_url):
            result = self._qualitative_offer_discoveries(lines, source_key, source_url, observed_at)
        return result

    def _promotion_discoveries(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        result: list[Discovery] = []
        seen: set[tuple[str, Decimal | None]] = set()
        active_expiry: datetime | None = None

        for index, line in enumerate(lines):
            range_match = _DATE_RANGE_RE.search(line)
            if range_match:
                active_expiry = _range_end(range_match, observed_at)

            amounts = _money_values(line)
            percent = _PERCENT_RE.search(line)
            if not amounts and not percent:
                continue

            title = _nearest_title(lines, index)
            if not title:
                continue

            original: Decimal | None = None
            current: Decimal | None = None
            if len(amounts) >= 2 and amounts[0] != amounts[1]:
                original = max(amounts[0], amounts[1])
                current = min(amounts[0], amounts[1])
            elif len(amounts) == 1 and percent:
                current = amounts[0]
            elif not percent:
                continue

            key = (title.casefold(), current)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.DEAL,
                    entity_id=None,
                    title=title,
                    source_key=source_key,
                    source_url=source_url,
                    observed_at=observed_at,
                    expires_at=active_expiry,
                    original_price=original,
                    current_price=current,
                    currency="EUR" if amounts else None,
                    freshness=FreshnessState.UNVERIFIED,
                )
            )
        return result

    def _qualitative_offer_discoveries(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        result: list[Discovery] = []
        seen: set[str] = set()
        ignored = {"offers", "special offers"}
        for line in lines:
            clean = line.strip()
            folded = clean.casefold()
            if folded in ignored or folded in seen:
                continue
            if len(clean) > 80 or len(clean.split()) > 8:
                continue
            if not _QUALITATIVE_OFFER_RE.search(clean):
                continue
            seen.add(folded)
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.DEAL,
                    entity_id=None,
                    title=clean[:180],
                    source_key=source_key,
                    source_url=source_url,
                    observed_at=observed_at,
                    freshness=FreshnessState.UNVERIFIED,
                )
            )
        return result

    def _event_discoveries(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        result: list[Discovery] = []
        seen: set[str] = set()

        for index, line in enumerate(lines):
            range_match = _DATE_RANGE_RE.search(line)
            numeric_match = _NUMERIC_DATE_RE.search(line)
            if not (_EVENT_DATE_RE.search(line) or range_match or numeric_match):
                continue
            title = _event_title(lines, index, source_url)
            if not title or title.casefold() in seen:
                continue

            starts_at = (
                _range_start(range_match, observed_at)
                if range_match
                else parse_discovery_date(line, observed_at=observed_at)
            )
            if starts_at is None and numeric_match:
                starts_at = _numeric_date(numeric_match, observed_at)
            if starts_at is None and not range_match:
                continue

            seen.add(title.casefold())
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.EVENT,
                    entity_id=None,
                    title=title,
                    source_key=source_key,
                    source_url=source_url,
                    observed_at=observed_at,
                    starts_at=starts_at,
                    expires_at=_range_end(range_match, observed_at) if range_match else None,
                    freshness=FreshnessState.UNVERIFIED,
                )
            )
        return result

    def _current_listing_events(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        result: list[Discovery] = []
        seen: set[str] = set()
        for index, line in enumerate(lines):
            folded = line.casefold()
            if "buy tickets" not in folded:
                continue
            before = re.split(r"buy tickets", line, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -|•")
            title = before if len(before) >= 3 else _nearest_title(lines, index)
            if not title:
                continue
            key = title.casefold()
            if key in seen or key in _IGNORED_TITLE_LINES:
                continue
            seen.add(key)
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.EVENT,
                    entity_id=None,
                    title=title[:180],
                    source_key=source_key,
                    source_url=source_url,
                    observed_at=observed_at,
                    freshness=FreshnessState.UNVERIFIED,
                )
            )
        return result


def _clean_lines(lines: Iterable[str]) -> Iterable[str]:
    for raw in lines:
        line = re.sub(r"\s+", " ", raw).strip(" \t|•")
        if 2 <= len(line) <= 240:
            yield line


def _money_values(line: str) -> list[Decimal]:
    if "€" not in line and "EUR" not in line.upper():
        return []
    values: list[Decimal] = []
    for match in _MONEY_RE.finditer(line):
        raw = match.group(1).replace(",", ".")
        try:
            values.append(Decimal(raw))
        except Exception:
            continue
    return values


def _event_title(lines: tuple[str, ...], index: int, source_url: str) -> str | None:
    host = (urlsplit(source_url).hostname or "").casefold()
    if host.endswith("visitmalta.com"):
        return _following_title(lines, index) or _nearest_title(lines, index)
    return _nearest_title(lines, index) or _following_title(lines, index)


def _following_title(lines: tuple[str, ...], index: int) -> str | None:
    for offset in range(1, 4):
        candidate_index = index + offset
        if candidate_index >= len(lines):
            break
        candidate = lines[candidate_index]
        if _valid_title_candidate(candidate):
            return candidate[:180]
    return None


def _nearest_title(lines: tuple[str, ...], index: int) -> str | None:
    for offset in range(1, 5):
        candidate_index = index - offset
        if candidate_index < 0:
            break
        candidate = lines[candidate_index]
        if _valid_title_candidate(candidate):
            return candidate[:180]
    return None


def _valid_title_candidate(candidate: str) -> bool:
    folded = candidate.casefold().strip()
    if folded in _IGNORED_TITLE_LINES:
        return False
    if _DATE_RANGE_RE.fullmatch(candidate) or _NUMERIC_DATE_RE.fullmatch(candidate):
        return False
    if _money_values(candidate) or _PERCENT_RE.search(candidate):
        return False
    return len(candidate) >= 3


def _range_start(match: re.Match[str] | None, observed_at: datetime) -> datetime | None:
    if match is None:
        return None
    year = int(match.group("start_year")) if match.group("start_year") else observed_at.year
    try:
        return datetime(
            year,
            int(match.group("start_month")),
            int(match.group("start_day")),
            tzinfo=observed_at.tzinfo or timezone.utc,
        )
    except ValueError:
        return None


def _range_end(match: re.Match[str] | None, observed_at: datetime) -> datetime | None:
    if match is None:
        return None
    start_year = int(match.group("start_year")) if match.group("start_year") else observed_at.year
    end_year = int(match.group("end_year")) if match.group("end_year") else start_year
    start_month = int(match.group("start_month"))
    end_month = int(match.group("end_month"))
    if not match.group("end_year") and end_month < start_month:
        end_year += 1
    try:
        return datetime(
            end_year,
            end_month,
            int(match.group("end_day")),
            hour=23,
            minute=59,
            second=59,
            tzinfo=observed_at.tzinfo or timezone.utc,
        )
    except ValueError:
        return None


def _numeric_date(match: re.Match[str], observed_at: datetime) -> datetime | None:
    year = int(match.group("year")) if match.group("year") else observed_at.year
    try:
        return datetime(
            year,
            int(match.group("month")),
            int(match.group("day")),
            tzinfo=observed_at.tzinfo or timezone.utc,
        )
    except ValueError:
        return None


def _is_offer_listing_url(source_url: str) -> bool:
    path = (urlsplit(source_url).path or "").casefold()
    return "offer" in path or "deal" in path


def _is_current_listing_url(source_url: str) -> bool:
    path = (urlsplit(source_url).path or "").casefold().rstrip("/")
    return path.endswith("/whats-on") or path.endswith("/what-s-on")
