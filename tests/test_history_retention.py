from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

from donmulwon2.storage import AnalysisStore


def test_recent_analyses_purges_records_older_than_five_days(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")
    payload = {"matched": True, "latest": {"close": 1250}, "weekly": {"grade": "A"}}
    store.save_analysis("005930", "삼성전자", "20261114", payload)

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE analysis_history SET analyzed_at = ? WHERE ticker = ?",
            ((datetime.now() - timedelta(days=5, seconds=1)).isoformat(timespec="seconds"), "005930"),
        )
        conn.execute(
            """INSERT INTO analysis_history
               (analyzed_at, ticker, name, trading_date, matched, payload)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(timespec="seconds"), "000660", "SK하이닉스",
             "20261114", 1, json.dumps({"latest": {"close": 200000}}, ensure_ascii=False)),
        )

    items = store.recent_analyses()
    assert len(items) == 1
    assert items[0]["ticker"] == "000660"
    assert items[0]["baseline_price"] == 200000

    with sqlite3.connect(store.db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0]
    assert remaining == 1
