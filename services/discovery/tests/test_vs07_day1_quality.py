from decimal import Decimal

from ziras_discovery.adapters.public_web import _money_values


def test_money_parser_ignores_attendee_counts_next_to_real_price() -> None:
    line = "Spend €35 and receive admission for 1 adult and 2 children"
    assert _money_values(line) == [Decimal("35")]


def test_money_parser_accepts_prefix_and_suffix_currency() -> None:
    assert _money_values("€24.00 now 18.00 EUR") == [Decimal("24.00"), Decimal("18.00")]
