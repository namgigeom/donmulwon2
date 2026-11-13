"""Network-free regression tests for KRX market data adapters."""
import unittest
from unittest.mock import patch
import os

import pandas as pd

from donmulwon2.market_data import KrxDataProvider


class KrxIndexLookupTests(unittest.TestCase):
    @patch("donmulwon2.market_data.stock.get_index_ohlcv_by_date")
    def test_latest_trading_date_disables_broken_index_name_mapping(self, get_index):
        get_index.return_value = pd.DataFrame(
            {"종가": [2500]}, index=pd.to_datetime(["2026-11-13"])
        )

        result = KrxDataProvider.latest_trading_date()

        self.assertEqual(result, "20261113")
        self.assertIs(get_index.call_args.kwargs["name_display"], False)

    @patch.dict(os.environ, {"KRX_ID": "", "KRX_PW": ""})
    @patch("donmulwon2.market_data.stock.get_index_ohlcv_by_date", side_effect=ValueError("Expecting value: line 1 column 1"))
    def test_missing_krx_credentials_get_actionable_error(self, get_index):
        with self.assertRaisesRegex(RuntimeError, "KRX_ID와 KRX_PW"):
            KrxDataProvider.latest_trading_date()

    @patch("donmulwon2.market_data.stock.get_index_ohlcv_by_date")
    def test_index_history_disables_broken_index_name_mapping(self, get_index):
        frame = pd.DataFrame(
            {"종가": [2500]}, index=pd.to_datetime(["2026-11-13"])
        )
        get_index.return_value = frame

        result = KrxDataProvider().index_history("1001", days=10)

        self.assertTrue(result.ok)
        self.assertIs(get_index.call_args.kwargs["name_display"], False)


if __name__ == "__main__":
    unittest.main()
