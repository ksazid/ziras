from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Sequence

from .domain import Discovery, SourceObservation


@dataclass(frozen=True, slots=True)
class RenderedPage:
    url: str
    html: str
    rendered_at: datetime


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    latitude: float
    longitude: float
    label: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class SourceAdapterResult:
    observation: SourceObservation
    discoveries: tuple[Discovery, ...]


class SourceAdapter(Protocol):
    name: str

    def extract(
        self,
        *,
        source_key: str,
        source_url: str,
        html: str,
        observed_at: datetime,
        content_hash: str,
    ) -> SourceAdapterResult: ...


class BrowserRenderer(Protocol):
    def render(self, url: str) -> RenderedPage: ...


class Geocoder(Protocol):
    def geocode(self, query: str) -> Sequence[GeocodeResult]: ...

    def reverse(self, latitude: float, longitude: float) -> Sequence[GeocodeResult]: ...


class JobQueue(Protocol):
    def enqueue(self, task_name: str, payload: dict[str, object], *, priority: int = 0) -> str: ...

    def schedule(self, task_name: str, payload: dict[str, object], *, run_at: datetime, priority: int = 0) -> str: ...


class Ranker(Protocol):
    def rank(self, discoveries: Sequence[Discovery], *, context: dict[str, object]) -> Sequence[Discovery]: ...
