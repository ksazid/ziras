from __future__ import annotations

from scrapling import Selector

from common import write_results

BEFORE = """
<html><body><section class='offers'>
<article id='deal-card' class='promo-card food-offer' data-brand='Tikka Masala'>
<h2>Tikka Masala</h2><span class='price'>€18.00</span><span class='discount'>25% off</span>
</article></section></body></html>
"""

AFTER = """
<html><body><main><div class='campaign-grid'>
<div id='campaign-2026-08' class='offer-tile featured' data-brand='Tikka Masala'>
<div class='copy'><h3>Tikka Masala</h3><strong class='current-price'>€18.00</strong><em>25% off</em></div>
</div></main></body></html>
"""


def main():
    url = "https://fixture.ziras.local/deals"
    first = Selector(BEFORE, adaptive=True, url=url)
    original = first.css("#deal-card", identifier="offer-card", auto_save=True)
    second = Selector(AFTER, adaptive=True, url=url)
    recovered = second.css("#deal-card", identifier="offer-card", adaptive=True, percentage=30)
    text = recovered[0].get_all_text(separator=" ", strip=True) if recovered else ""
    result = {
        "id": "scrapling-adaptive-dom-change",
        "class": "selector-resilience",
        "adapter": "scrapling-parser",
        "original_found": bool(original),
        "recovered_found": bool(recovered),
        "recovered_text": str(text),
        "status": "PASS" if recovered and "Tikka Masala" in str(text) and "25%" in str(text) else "FAIL",
        "fetcher_used": False,
        "stealth_used": False,
    }
    write_results("scrapling-adaptive", [result])


if __name__ == "__main__":
    main()
