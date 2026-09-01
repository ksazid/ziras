from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import re
from typing import Iterable
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import trafilatura

from ..domain import Discovery, DiscoveryType, FreshnessState, SourceObservation
from ..extraction import parse_discovery_date
from ..ports import SourceAdapterResult
from .structured_html import StructuredHtmlAdapter


_MONEY_RE = re.compile(
    r"(?P<decimal>\d{1,4}[.,]\d{1,2})|"
    r"(?:(?:€|EUR)\s*(?P<prefix_int>\d{1,4})(?![\d.,])|"
    r"(?P<suffix_int>\d{1,4})(?![\d.,])\s*(?:€|EUR))",
    re.IGNORECASE,
)
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
_PROMOTION_WORDS = (
    "offer",
    "deal",
    "discount",
    "loyalty",
    "combo",
    "saving",
    "sale",
    "promotion",
    "package",
    "voucher",
    "day pass",
    "retreat",
)
_GENERIC_PROMOTION_TITLES = {
    "offer",
    "offers",
    "special offer",
    "special offers",
    "deal",
    "deals",
    "sale",
    "promotion",
    "promotions",
    "package",
    "packages",
    "voucher",
    "vouchers",
    "gift voucher",
    "gift vouchers",
    "the offer",
    "our offers",
}
_GENERIC_EVENT_TITLES = {
    "event",
    "events",
    "what's on",
    "what’s on",
    "coming soon",
    "buy tickets",
    "book tickets",
    "tickets",
    "more info",
    "view all events",
    "view all",
    "skip to content",
}
_ACTION_NOISE = (
    "add to cart",
    "add to wishlist",
    "add to compare",
    "sort by",
    "display",
    "search",
)
_POLICY_NOISE = ("terms", "conditions", "privacy", "policy")
_PROMOTION_ACTION_PREFIXES = (
    "back to ",
    "book ",
    "claim ",
    "explore ",
    "apply ",
    "view ",
    "learn more",
    "read more",
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

        # Offer-detail pages frequently contain site-wide related-offer rails and JSON-LD.
        # For a detail route, the page's own H1 is the authoritative discovery boundary.
        if not self.config.event_mode and _is_promotion_detail_url(source_url):
            discoveries = self._promotion_detail_discoveries(
                html,
                source_key,
                source_url,
                observed_at,
            )
            raw_lines = tuple(_clean_lines(_raw_text_nodes(html)))
            observation = SourceObservation(
                id=uuid4(),
                source_key=source_key,
                source_url=source_url,
                observed_at=observed_at,
                content_hash=digest,
                extracted={
                    "raw_text_line_count": len(raw_lines),
                    "candidate_count": len(discoveries),
                    "mode": "promotion-detail",
                },
                adapter=self.name,
            )
            return SourceAdapterResult(
                observation=observation,
                discoveries=tuple(discoveries[: self.config.maximum_discoveries]),
            )

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
        precision_lines = tuple(_clean_lines(text.splitlines()))
        raw_lines = tuple(_clean_lines(_raw_text_nodes(html)))

        if self.config.event_mode:
            discoveries = _merge_discoveries(
                self._event_discoveries(precision_lines, source_key, source_url, observed_at),
                self._event_discoveries(raw_lines, source_key, source_url, observed_at),
                self._event_link_discoveries(html, source_key, source_url, observed_at),
                self._event_ticket_line_discoveries(raw_lines, source_key, source_url, observed_at),
            )
        else:
            discoveries = _merge_discoveries(
                self._promotion_product_block_discoveries(html, source_key, source_url, observed_at),
                self._promotion_discoveries(precision_lines, source_key, source_url, observed_at),
                self._promotion_discoveries(raw_lines, source_key, source_url, observed_at),
                self._promotion_heading_discoveries(raw_lines, source_key, source_url, observed_at),
            )

        observation = SourceObservation(
            id=uuid4(),
            source_key=source_key,
            source_url=source_url,
            observed_at=observed_at,
            content_hash=digest,
            extracted={
                "text_line_count": len(precision_lines),
                "raw_text_line_count": len(raw_lines),
                "candidate_count": len(discoveries),
                "mode": "event" if self.config.event_mode else "promotion",
            },
            adapter=self.name,
        )
        return SourceAdapterResult(
            observation=observation,
            discoveries=tuple(discoveries[: self.config.maximum_discoveries]),
        )

    def _promotion_detail_discoveries(
        self,
        html: str,
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        parser = _H1Parser()
        parser.feed(html)
        title = next((item for item in parser.values if _useful_promotion_title(item)), None)
        if not title:
            return []
        return [
            Discovery(
                id=uuid4(),
                discovery_type=DiscoveryType.DEAL,
                entity_id=None,
                title=title[:180],
                source_key=source_key,
                source_url=source_url,
                observed_at=observed_at,
                freshness=FreshnessState.UNVERIFIED,
            )
        ]

    def _promotion_product_block_discoveries(
        self,
        html: str,
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        parser = _HeadingBlockParser()
        parser.feed(html)
        parser.finish()
        sale_context = urlsplit(source_url).path.casefold().rstrip("/").endswith("/sale")
        result: list[Discovery] = []
        seen: set[str] = set()

        for title, body in parser.blocks:
            folded = title.casefold()
            body_folded = body.casefold()
            if not _useful_promotion_title(title):
                continue
            if not _looks_like_title(title) or "add to cart" not in body_folded:
                continue
            amounts = _money_values(body)
            percent = _PERCENT_RE.search(f"{title} {body}")
            if not amounts:
                continue

            current: Decimal | None = None
            original: Decimal | None = None
            if len(amounts) >= 2 and min(amounts) != max(amounts):
                current = min(amounts)
                original = max(amounts)
            elif sale_context or percent:
                current = amounts[0]
            else:
                continue

            if folded in seen:
                continue
            seen.add(folded)
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.DEAL,
                    entity_id=None,
                    title=title[:180],
                    source_key=source_key,
                    source_url=source_url,
                    observed_at=observed_at,
                    original_price=original,
                    current_price=current,
                    currency="EUR",
                    freshness=FreshnessState.UNVERIFIED,
                )
            )
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
            if not title or not _useful_promotion_title(title):
                continue

            original: Decimal | None = None
            current: Decimal | None = None
            if len(amounts) >= 2 and amounts[0] != amounts[-1]:
                if "weekday" in line.casefold() or "weekend" in line.casefold():
                    continue
                current = min(amounts[0], amounts[-1])
                original = max(amounts[0], amounts[-1])
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

    def _promotion_heading_discoveries(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        result: list[Discovery] = []
        seen: set[str] = set()
        for line in lines:
            folded = line.casefold()
            if not any(word in folded for word in _PROMOTION_WORDS):
                continue
            if re.fullmatch(r"sale\s+\d{1,2}%", folded):
                continue
            if not _useful_promotion_title(line) or not _looks_like_title(line):
                continue
            if folded in seen:
                continue
            seen.add(folded)
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.DEAL,
                    entity_id=None,
                    title=line[:180],
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

    def _event_ticket_line_discoveries(
        self,
        lines: tuple[str, ...],
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        result: list[Discovery] = []
        seen: set[str] = set()
        for index, line in enumerate(lines):
            if "buy tickets" not in line.casefold():
                continue
            title = re.sub(r"\bbuy tickets\b", "", line, flags=re.IGNORECASE).strip(" -–|:")
            if not _looks_like_title(title) or title.casefold() in _GENERIC_EVENT_TITLES:
                title = _nearest_title(lines, index) or ""
            folded = title.casefold()
            if not title or folded in _GENERIC_EVENT_TITLES or folded in seen:
                continue
            seen.add(folded)
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

    def _event_link_discoveries(
        self,
        html: str,
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> list[Discovery]:
        parser = _AnchorParser()
        parser.feed(html)
        grouped: dict[str, list[str]] = {}
        for href, text in parser.anchors:
            if not href or not text:
                continue
            grouped.setdefault(urljoin(source_url, href), []).append(text)

        result: list[Discovery] = []
        seen: set[str] = set()
        for href, texts in grouped.items():
            href_path = urlsplit(href).path.casefold()
            has_ticket_signal = any("ticket" in item.casefold() or item.casefold() == "more info" for item in texts)
            has_event_path = "/event/" in href_path
            if not has_ticket_signal and not has_event_path:
                continue
            title = next(
                (
                    item
                    for item in texts
                    if item.casefold() not in _GENERIC_EVENT_TITLES and _looks_like_title(item)
                ),
                None,
            )
            if not title or title.casefold() in seen:
                continue
            seen.add(title.casefold())
            result.append(
                Discovery(
                    id=uuid4(),
                    discovery_type=DiscoveryType.EVENT,
                    entity_id=None,
                    title=title[:180],
                    source_key=source_key,
                    source_url=href,
                    observed_at=observed_at,
                    freshness=FreshnessState.UNVERIFIED,
                )
            )
        return result


def _is_promotion_detail_url(source_url: str) -> bool:
    path = urlsplit(source_url).path.casefold().rstrip("/")
    for marker in ("/special-offers/", "/offers/"):
        if marker in path and path.split(marker, 1)[1].strip("/"):
            return True
    return False


def _useful_promotion_title(value: str) -> bool:
    folded = re.sub(r"\s+", " ", value.casefold()).strip(" -–|:")
    if not folded or folded in _GENERIC_PROMOTION_TITLES:
        return False
    if any(noise in folded for noise in _POLICY_NOISE):
        return False
    if "t&c" in folded or "t & c" in folded or folded.startswith("not valid with"):
        return False
    if folded.endswith("?") or folded.startswith(("faq", "faqs")):
        return False
    if any(folded.startswith(prefix) for prefix in _PROMOTION_ACTION_PREFIXES):
        return False
    if re.fullmatch(r"promotion\s+\d+", folded):
        return False
    if re.fullmatch(r"\d+\s*/\s*\d+", folded):
        return False
    if folded.startswith(("age:", "- age:", "discount when buying")):
        return False
    return True


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
        raw = (match.group("decimal") or match.group("prefix_int") or match.group("suffix_int")).replace(",", ".")
        try:
            values.append(Decimal(raw))
        except Exception:
            continue
    return values


def _nearest_title(lines: tuple[str, ...], index: int) -> str | None:
    for offset in range(1, 6):
        candidate_index = index - offset
        if candidate_index < 0:
            break
        candidate = lines[candidate_index]
        folded = candidate.casefold()
        if _DATE_RANGE_RE.fullmatch(candidate):
            continue
        if _money_values(candidate) or _PERCENT_RE.search(candidate):
            continue
        if any(noise in folded for noise in _ACTION_NOISE):
            continue
        if not _useful_promotion_title(candidate):
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


def _looks_like_title(value: str) -> bool:
    folded = value.casefold().strip()
    if len(value) > 100 or len(value.split()) > 14:
        return False
    if any(noise in folded for noise in _ACTION_NOISE):
        return False
    if value.rstrip().endswith((".", ";")):
        return False
    return len(value) >= 3


def _merge_discoveries(*groups: Iterable[Discovery]) -> list[Discovery]:
    result: list[Discovery] = []
    seen: set[tuple[object, ...]] = set()
    for group in groups:
        for item in group:
            key = (
                item.discovery_type.value,
                item.title.casefold(),
                item.current_price,
                item.starts_at,
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def _raw_text_nodes(html: str) -> tuple[str, ...]:
    parser = _TextNodeParser()
    parser.feed(html)
    return tuple(parser.values)


class _H1Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []
        self._inside = False
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        folded = tag.casefold()
        if folded in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if not self._skip_depth and folded == "h1":
            self._inside = True
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        folded = tag.casefold()
        if folded in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if not self._skip_depth and folded == "h1" and self._inside:
            text = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            if text:
                self.values.append(text)
            self._inside = False
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._inside and not self._skip_depth and data.strip():
            self._parts.append(data.strip())


class _TextNodeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.casefold() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.values.append(data)


class _HeadingBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._skip_depth = 0
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._active_heading: str | None = None
        self._body_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        folded = tag.casefold()
        if folded in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if not self._skip_depth and folded in {"h1", "h2", "h3", "h4"}:
            self._flush_block()
            self._heading_tag = folded
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        folded = tag.casefold()
        if folded in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if not self._skip_depth and self._heading_tag == folded:
            title = re.sub(r"\s+", " ", " ".join(self._heading_parts)).strip()
            self._active_heading = title or None
            self._heading_tag = None
            self._heading_parts = []
            self._body_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data.strip():
            return
        if self._heading_tag is not None:
            self._heading_parts.append(data.strip())
        elif self._active_heading is not None:
            self._body_parts.append(data.strip())

    def finish(self) -> None:
        self._flush_block()

    def _flush_block(self) -> None:
        if self._active_heading:
            body = re.sub(r"\s+", " ", " ".join(self._body_parts)).strip()
            self.blocks.append((self._active_heading, body))
        self._active_heading = None
        self._body_parts = []


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.casefold() != "a":
            return
        self._href = next((value for key, value in attrs if key.casefold() == "href"), None)
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None and data.strip():
            self._parts.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self._href is None:
            return
        text = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
        if text:
            self.anchors.append((self._href, text))
        self._href = None
        self._parts = []
