"""Persistence tests for local SQLite records."""
import tempfile
import unittest
from pathlib import Path

from donmulwon2.storage import AnalysisStore


class StorageTests(unittest.TestCase):
    def test_market_bulletin_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AnalysisStore(Path(directory) / "test.db")
            payload = {"advancers": 700, "decliners": 500, "stale": False}
            store.save_bulletin("20261112", "KOSPI", payload)
            self.assertEqual(store.latest_bulletin("KOSPI"), payload)

    def test_analysis_history_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AnalysisStore(Path(directory) / "test.db")
            payload = {"matched": True, "rsi10": 62.5}
            store.save_analysis("005930", "삼성전자", "20261112", payload)
            records = store.recent_analyses()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["ticker"], "005930")
            self.assertEqual(records[0]["payload"], payload)
            self.assertTrue(records[0]["matched"])


if __name__ == "__main__":
    unittest.main()
