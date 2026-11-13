import unittest

import pandas as pd

from donmulwon2.market_data import _company_profile_from_data


class CompanyProfileTests(unittest.TestCase):
    def test_builds_company_summary_financials_and_analyst_outlook(self):
        annual = pd.DataFrame(
            {
                pd.Timestamp("2025-12-31"): [1200, 180, 140],
                pd.Timestamp("2024-12-31"): [1000, 150, 110],
            },
            index=["Total Revenue", "Operating Income", "Net Income"],
        )
        quarterly = pd.DataFrame(
            {pd.Timestamp("2026-06-30"): [340, 55, 42]},
            index=["Total Revenue", "Operating Income", "Net Income"],
        )
        profile = _company_profile_from_data(
            "000000.KS",
            {
                "longBusinessSummary": "기업의 주요 사업 설명",
                "sector": "Technology",
                "industry": "Semiconductors",
                "currency": "KRW",
                "marketCap": 9000,
                "targetMeanPrice": 12000,
                "recommendationKey": "buy",
                "numberOfAnalystOpinions": 8,
            },
            annual,
            quarterly,
            10000,
        )
        self.assertTrue(profile["available"])
        self.assertEqual(profile["sector"], "Technology")
        self.assertEqual(profile["annual"]["revenue"], 1200.0)
        self.assertEqual(profile["annual"]["revenue_growth_pct"], 20.0)
        self.assertEqual(profile["annual"]["operating_income"], 180.0)
        self.assertEqual(profile["quarterly"]["net_income"], 42.0)
        self.assertEqual(profile["outlook"]["target_upside_pct"], 20.0)
        self.assertEqual(profile["outlook"]["analyst_count"], 8)

    def test_missing_company_data_is_not_fabricated(self):
        profile = _company_profile_from_data("000000.KS", {}, None, None, None)
        self.assertFalse(profile["available"])
        self.assertIsNone(profile["annual"])
        self.assertIsNone(profile["quarterly"])
        self.assertIsNone(profile["outlook"]["target_mean_price"])


if __name__ == "__main__":
    unittest.main()
