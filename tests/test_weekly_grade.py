"""Deterministic tests for weekly trend grading."""
import unittest

import pandas as pd

from donmulwon2.analyzer import _weekly_summary


class WeeklyTrendGradeTests(unittest.TestCase):
    def _frame(self, current, previous=None):
        previous = previous or {
            "MA10": 100.0,
            "MA20": 95.0,
            "RSI10": 55.0,
            "RSI14": 50.0,
        }
        return pd.DataFrame(
            [previous, current],
            index=pd.to_datetime(["2026-10-30", "2026-11-06"]),
        )

    def test_strong_weekly_uptrend_is_grade_a(self):
        result = _weekly_summary(self._frame({
            "종가": 120.0, "MA10": 110.0, "MA20": 100.0,
            "RSI10": 65.0, "RSI14": 55.0,
            "MACD": 3.0, "MACD_SIGNAL": 2.0,
        }))
        self.assertEqual(result["grade"], "A")
        self.assertEqual(result["grade_score"], 100)
        self.assertEqual(result["trend"], "강한 상승 추세")

    def test_moderate_weekly_setup_is_grade_b(self):
        result = _weekly_summary(self._frame({
            "종가": 108.0, "MA10": 105.0, "MA20": 100.0,
            "RSI10": 48.0, "RSI14": 52.0,
            "MACD": 1.0, "MACD_SIGNAL": 2.0,
        }, previous={
            "MA10": 105.0, "MA20": 100.0, "RSI10": 55.0, "RSI14": 50.0,
        }))
        self.assertEqual(result["grade"], "B")
        self.assertEqual(result["grade_score"], 55)

    def test_weak_weekly_setup_is_grade_c(self):
        result = _weekly_summary(self._frame({
            "종가": 80.0, "MA10": 90.0, "MA20": 100.0,
            "RSI10": 35.0, "RSI14": 45.0,
            "MACD": -3.0, "MACD_SIGNAL": -2.0,
        }))
        self.assertEqual(result["grade"], "C")
        self.assertEqual(result["trend"], "혼조·하락 추세")

    def test_insufficient_weekly_data_defaults_to_c(self):
        result = _weekly_summary(pd.DataFrame())
        self.assertEqual(result["grade"], "C")
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
