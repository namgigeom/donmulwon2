from __future__ import annotations

from donmulwon2.raccoon_ai import build_market_facts
from donmulwon2.storage import AnalysisStore


def test_build_market_facts_uses_only_supplied_market_data():
    facts = build_market_facts([
        {
            "date": "20261114",
            "advancers": 500,
            "decliners": 300,
            "trading_value": 123456,
            "index": {"close": 2700, "change_pct": 0.8},
            "sectors": [
                {"name": "반도체", "change_pct": 2.4, "stock_count": 12},
                {"name": "화학", "change_pct": -1.2, "stock_count": 8},
            ],
            "investor_flows": {"values": {"외국인": 500000000}},
            "market": "KOSPI",
        }
    ])

    market = facts["markets"][0]
    assert market["date"] == "20261114"
    assert market["index"]["close"] == 2700
    assert market["strongest_sectors"][0]["name"] == "반도체"
    assert market["weakest_sectors"][0]["name"] == "화학"
    assert market["investor_flows"]["외국인"] == 500000000
    assert market["advancers"] == 500


def test_raccoon_note_is_cached_by_trading_date(tmp_path):
    store = AnalysisStore(tmp_path / "market.db")
    facts = {"markets": [{"market": "KOSPI", "date": "20261114"}]}
    store.save_raccoon_note("20261114", "오늘은 관망하자너굴", "test/model", facts)

    saved = store.get_raccoon_note("20261114")
    assert saved is not None
    assert saved["note"] == "오늘은 관망하자너굴"
    assert saved["model"] == "test/model"
    assert saved["trading_date"] == "20261114"
    assert store.get_raccoon_note("20261115") is None
