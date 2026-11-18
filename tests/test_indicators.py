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
            "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "VOLUME_MA10",
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


    def test_latest_signal_accepts_golden_cross_on_current_day(self):
        from unittest.mock import patch

        index = pd.date_range("2026-01-01", periods=3, freq="B")
        frame = pd.DataFrame(index=index, data={
            "RSI10": [44.0, 45.0, 49.0], "RSI14": [46.0, 46.0, 47.0],
            "MACD": [0.05, 0.10, 0.20], "MACD_SIGNAL": [0.08, 0.12, 0.15],
            "MACD_HIST": [-0.03, -0.02, 0.05],
            "MA10": [100.0, 101.0, 102.0], "종가": [99, 100, 105],
            "거래량": [1000, 1000, 1000], "VOLUME_MA10": [1000, 1000, 1000],
        })
        with patch("donmulwon2.indicators.calculate_indicators", return_value=frame):
            result = latest_signal(frame)
        self.assertEqual(result["timing"], "same_day")
        self.assertTrue(result["checks"]["rsi_cross_and_rising"])
        self.assertTrue(result["checks"]["macd_cross_and_rising"])

    def test_latest_signal_accepts_next_day_momentum_confirmation(self):
        from unittest.mock import patch

        index = pd.date_range("2026-01-01", periods=3, freq="B")
        frame = pd.DataFrame(index=index, data={
            "RSI10": [44.0, 50.0, 53.0], "RSI14": [46.0, 48.0, 49.0],
            "MACD": [0.10, 0.30, 0.42], "MACD_SIGNAL": [0.20, 0.25, 0.31],
            "MACD_HIST": [-0.10, 0.05, 0.11],
            "MA10": [100.0, 101.0, 102.0], "종가": [99, 100, 105],
            "거래량": [1000, 1000, 1000], "VOLUME_MA10": [1000, 1000, 1000],
        })
        with patch("donmulwon2.indicators.calculate_indicators", return_value=frame):
            result = latest_signal(frame)
        self.assertEqual(result["timing"], "next_day_confirmed")
        self.assertTrue(result["checks"]["rsi_cross_and_rising"])
        self.assertTrue(result["checks"]["macd_cross_and_rising"])
        self.assertTrue(result["checks"]["ma10_breakout"])

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


class VolumeMovingAverageTests(unittest.TestCase):
    def test_volume_average_uses_ten_sessions(self):
        import pandas as pd
        from donmulwon2.indicators import calculate_indicators

        index = pd.date_range("2026-01-01", periods=12, freq="B")
        frame = pd.DataFrame({
            "시가": range(100, 112),
            "고가": range(101, 113),
            "저가": range(99, 111),
            "종가": range(100, 112),
            "거래량": [100] * 10 + [200, 300],
        }, index=index)
        result = calculate_indicators(frame)
        self.assertAlmostEqual(result.iloc[-1]["VOLUME_MA10"], 130.0)
        self.assertNotIn("VOLUME_MA20", result.columns)
