"""Tests for transparent ATR-based reference levels."""
import unittest

from donmulwon2.analyzer import _trade_plan


class TradePlanTests(unittest.TestCase):
    def test_reference_levels_have_two_to_one_and_three_to_one_reward_risk(self):
        plan = _trade_plan(1000, 20)
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["entry_low"], 994.0)
        self.assertEqual(plan["entry_high"], 1004.0)
        self.assertEqual(plan["stop_loss"], 970.0)
        self.assertEqual(plan["target_1"], 1072.0)
        self.assertEqual(plan["target_2"], 1106.0)
        self.assertEqual(plan["reward_risk_1"], 2.0)
        self.assertEqual(plan["reward_risk_2"], 3.0)

    def test_missing_atr_returns_not_ready(self):
        self.assertFalse(_trade_plan(1000, None)["ready"])


if __name__ == "__main__":
    unittest.main()
