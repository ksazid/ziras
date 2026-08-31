from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import re
from typing import Iterable
from uuid import uuid4

import trafilatura

from ..domain import Discovery, DiscoveryType, FreshnessState, SourceObservation
from ..extraction import parse_discovery_date
from ..ports import SourceAdapterResult
from .structured_html import StructuredHtmlAdapter


_MONEY_RE = re.compile(r"(?:(?:€|EUR)\s*)?(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:€|EUR)?", re.IGNORECASE)
_PERCENT_RE = re.compile(r"\b(\d{1,2})\s*%\s*(?:off)?\b", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(
    r"(?P<start_day>\d{1,2})[./](?P<start_month>\d{1,2})\s*[-–]\s*"
    r"(?P<end_day>\d{1,2})[./](?P<end_month>\d{1,2})"
)
_EVENT_DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+\d{1,2})?(?:,?\s+\d{4})?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class TextSignalConfig:
    event_mode: bool = False
    maximum_discoveries: int = 100


class PublicWebSignalAdapter:
    """Deterministic public-page normalizer used after policy-approved acquisition."""

    name = "public-web-signal-v1"

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
            favor_precision=True,
        ) or ""
        lines = tuple(_clean_lines(text.splitlines()))
        discoveries = (
            self._event_discoveries(lines, source_key, source_url, observed_at)
            if self.config.event_mode
            else self._promotion_discoveries(lines, source_key, source_url, observed_at)
        )

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
            },
            adapter=self.name,
        )
        return SourceAdapterResult(
            observation=observation,
            discoveries=tuple(discoveries[: self.config.maximum_discoveries]),
        )

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
            if len(amounts) >= 2 and amounts[-1] < amounts[0]:
                original, current = amounts[0], amounts[-1]
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
            if not (_EVENT_DATE_RE.search(line) or _DATE_RANGE_RE.search(line)):
                continue
            title = _nearest_title(lines, index)
            if not title or title.casefold() in seen:
                continue
            starts_at = parse_discovery_date(line, observed_at=observed_at)
            if starts_at is None and not _DATE_RANGE_RE.search(line):
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


def _nearest_title(lines: tuple[str, ...], index: int) -> str | None:
    for offset in range(1, 5):
        candidate_index = index - offset
        if candidate_index < 0:
            break
        candidate = lines[candidate_index]
        if _DATE_RANGE_RE.fullmatch(candidate):
            continue
        if _money_values(candidate) or _PERCENT_RE.search(candidate):
            continue
        if len(candidate) < 3:
            continue
        return candidate[:180]
    return None


def _range_end(match: re.Match[str], observed_at: datetime) -> datetime | None:
    end_day = int(match.group("end_day"))
    end_month = int(match.group("end_month"))
    year = observed_at.year
    start_month = int(match.group("start_month"))
    if end_month < start_month:
        year += 1
    try:
        return observed_at.replace(
            year=year,
            month=end_month,
            day=end_day,
            hour=23,
            minute=59,
            second=59,
            microsecond=0,
        )
    except ValueError:
        return None
