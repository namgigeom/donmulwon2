"""Deterministic tests for the technical-indicator core (no network required)."""
import unittest

import pandas as pd

from donmulwon2.indicators import calculate_indicators, latest_signal


def ohlcv(closes):
    values = pd.Series(closes, dtype="float64")
    return pd.DataFrame({
        "시가": values,
        "고가": values + 1,
        "저가": values - 1,
        "종가": values,
        "거래량": [1000 + i * 10 for i in range(len(values))],
        "거래대금": values * 1000,
    })


class IndicatorTests(unittest.TestCase):
    def test_expected_indicator_columns_are_created(self):
        frame = calculate_indicators(ohlcv(range(100, 401)))
        expected = {
            "RSI10", "RSI14", "MACD", "MACD_SIGNAL", "MACD_HIST",
            "MA10", "MA20", "MA60", "MA120", "MA240",
            "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "VOLUME_MA20",
            "ATR14", "HIGH20", "LOW20", "HIGH252",
        }
        self.assertTrue(expected.issubset(frame.columns))
        self.assertAlmostEqual(frame.iloc[-1]["RSI10"], 100.0, places=6)
        self.assertAlmostEqual(frame.iloc[-1]["RSI14"], 100.0, places=6)

    def test_flat_series_rsi_is_neutral_not_extreme(self):
        frame = calculate_indicators(ohlcv([100] * 300))
        self.assertAlmostEqual(frame.iloc[-1]["RSI10"], 50.0, places=6)
        self.assertAlmostEqual(frame.iloc[-1]["RSI14"], 50.0, places=6)

    def test_signal_requires_enough_history_and_returns_three_checks(self):
        too_short = latest_signal(ohlcv([100, 101, 102]))
        self.assertFalse(too_short["ready"])

        long_frame = ohlcv([100 + i * 0.2 for i in range(300)])
        result = latest_signal(long_frame)
        self.assertTrue(result["ready"])
        self.assertEqual(
            set(result["checks"]),
            {"rsi_cross_and_rising", "macd_cross_and_rising", "ma10_breakout"},
        )
        self.assertIsInstance(result["matched"], bool)


    def test_weekly_resample_aggregates_ohlcv_and_omits_partial_week(self):
        from donmulwon2.indicators import resample_weekly_ohlcv

        dates = pd.bdate_range("2026-01-05", periods=8)  # ends Wednesday
        frame = ohlcv(range(100, 108))
        frame.index = dates
        weekly = resample_weekly_ohlcv(frame)
        self.assertEqual(len(weekly), 1)
        self.assertEqual(int(weekly.iloc[0]["시가"]), 100)
        self.assertEqual(int(weekly.iloc[0]["종가"]), 104)
        self.assertEqual(int(weekly.iloc[0]["거래량"]), sum(1000 + i * 10 for i in range(5)))


if __name__ == "__main__":
    unittest.main()
