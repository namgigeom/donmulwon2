"""Local SQLite storage for market snapshots and stock analysis history."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


class AnalysisStore:
    def __init__(self, db_path: str | Path | None = None):
        root = Path(__file__).resolve().parent.parent
        self.db_path = Path(db_path) if db_path else root / "data" / "donmulwon2.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _purge_expired_analyses(self):
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=5)).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute("DELETE FROM analysis_history WHERE analyzed_at < ?", (cutoff,))

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analyzed_at TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    trading_date TEXT,
                    matched INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_bulletins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trading_date TEXT NOT NULL,
                    market TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(trading_date, market)
                )
            """)
        self._purge_expired_analyses()

    def save_analysis(self, ticker: str, name: str, trading_date: str, result: dict):
        self._purge_expired_analyses()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO analysis_history
                   (analyzed_at, ticker, name, trading_date, matched, payload)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(timespec="seconds"), ticker, name,
                 trading_date, int(bool(result.get("matched"))),
                 json.dumps(result, ensure_ascii=False)),
            )

    def save_bulletin(self, trading_date: str, market: str, payload: dict):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO market_bulletins
                   (trading_date, market, created_at, payload)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(trading_date, market) DO UPDATE SET
                   created_at=excluded.created_at, payload=excluded.payload""",
                (trading_date, market, datetime.now().isoformat(timespec="seconds"),
                 json.dumps(payload, ensure_ascii=False)),
            )

    def latest_bulletin(self, market: str):
        with self._connect() as conn:
            row = conn.execute(
                """SELECT payload FROM market_bulletins
                   WHERE market = ? ORDER BY trading_date DESC LIMIT 1""",
                (market,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def recent_analyses(self, limit: int = 100):
        """Return analyses from the last five days and purge expired rows."""
        self._purge_expired_analyses()
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT analyzed_at, ticker, name, trading_date, matched, payload
                   FROM analysis_history ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        items = []
        for row in rows:
            payload = json.loads(row[5])
            latest = payload.get("latest") or {}
            items.append({
                "analyzed_at": row[0], "ticker": row[1], "name": row[2],
                "trading_date": row[3], "matched": bool(row[4]),
                "baseline_price": latest.get("close"),
                "weekly": payload.get("weekly"),
                "signal": payload.get("signal"),
                "trade_plan": latest.get("trade_plan"),
                "payload": payload,
            })
        return items
