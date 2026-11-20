from __future__ import annotations

import pandas as pd

from donmulwon2 import us_market_data


def test_us_market_bulletin_combines_indices_breadth_and_sectors(monkeypatch):
    monkeypatch.setattr(us_market_data, "_last_completed_us_date", lambda: pd.Timestamp("2026-11-19"))
    monkeypatch.setattr(
        us_market_data, "_index_snapshot",
        lambda symbol, label, end_date: {
            "name": label, "close": 20000.0 if symbol == "^IXIC" else 6000.0,
            "change": 100.0, "change_pct": 0.5, "trend": [1.0, 2.0],
            "date": "2026-11-19",
        },
    )
    monkeypatch.setattr(
        us_market_data, "_breadth_and_turnover",
        lambda end_date: {
            "advancers": 1200, "decliners": 900, "unchanged": 100,
            "ticker_count": 2200, "universe_count": 3000,
            "trading_value": 1_500_000_000_000.0, "currency": "USD",
            "coverage_pct": 73.3, "error_count": 800,
        },
    )
    monkeypatch.setattr(
        us_market_data, "_sector_snapshot",
        lambda end_date: [{"name": "정보기술", "ticker": "XLK", "change_pct": 1.2,
                           "stock_count": 0, "market": "US"}],
    )
    monkeypatch.setattr(us_market_data, "_CACHE", None)

    result = us_market_data.us_market_bulletin(force_refresh=True)

    assert result["market"] == "US"
    assert result["indexes"]["nasdaq"]["name"] == "NASDAQ 종합"
    assert result["indexes"]["sp500"]["name"] == "S&P 500"
    assert result["advancers"] == 1200
    assert result["decliners"] == 900
    assert result["trading_value"] == 1_500_000_000_000.0
    assert result["sectors"][0]["ticker"] == "XLK"
    assert result["investor_flows"] is None
    assert "거래대금 $1500.0B" in result["one_line_summary"]
