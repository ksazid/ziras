from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, _money_values
from ziras_discovery.source_catalog import FetchMode, load_source_catalog


def test_money_parser_ignores_attendee_counts_next_to_real_price() -> None:
    line = "Spend €35 and receive admission for 1 adult and 2 children"
    assert _money_values(line) == [Decimal("35")]


def test_money_parser_accepts_integer_currency_adjacency_only() -> None:
    assert _money_values("€35 and 40 EUR") == [Decimal("35"), Decimal("40")]
    assert _money_values("€35 for 1 adult and 2 children") == [Decimal("35")]


def test_money_parser_accepts_prefix_and_suffix_currency() -> None:
    assert _money_values("€24.00 now 18.00 EUR") == [Decimal("24.00"), Decimal("18.00")]


def test_money_parser_preserves_prefixed_decimal_prices() -> None:
    assert _money_values("€70.00 €100.00") == [Decimal("70.00"), Decimal("100.00")]
    assert _money_values("€24.00 €18.00") == [Decimal("24.00"), Decimal("18.00")]


def test_money_parser_preserves_supermarket_old_and_new_decimal_prices() -> None:
    assert _money_values("1.79 1.39 €") == [Decimal("1.79"), Decimal("1.39")]


def test_eden_uses_browser_acquisition_after_live_static_202() -> None:
    by_key = {entry.source_key: entry for entry in load_source_catalog()}
    assert by_key["eden_cinemas"].fetch_mode is FetchMode.BROWSER


def test_esplora_policy_noise_is_rejected_but_real_package_is_retained() -> None:
    html = """
    <html><body><main>
      <h2>Promotions T&C’s</h2>
      <h2>Not valid with any other offer or Group discount</h2>
      <h2>Older Adults Group Packages</h2>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="esplora_family_promotions",
        source_url="https://esplora.org.mt/promotions-tcs/",
        html=html,
        observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    titles = [item.title for item in result.discoveries]
    assert "Promotions T&C’s" not in titles
    assert "Not valid with any other offer or Group discount" not in titles
    assert "Older Adults Group Packages" in titles


def test_poc_ingestion_serializes_full_ranked_inventory_for_audit() -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_poc_ingestion.py"
    text = script.read_text(encoding="utf-8")
    assert "summary.ranked[:100]" not in text
    assert "for item in summary.ranked" in text
