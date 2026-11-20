import pandas as pd

from donmulwon2.us_market_scanner import _to_frame


def test_to_frame_converts_yahoo_daily_columns():
    index = pd.date_range("2026-10-01", periods=2, freq="B")
    source = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 12.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 11.5],
            "Volume": [1000, 2000],
        },
        index=index,
    )
    result = _to_frame(source, "TEST")
    assert list(result.columns) == ["시가", "고가", "저가", "종가", "거래량", "거래대금"]
    assert result.iloc[-1]["거래대금"] == 23000.0


def test_to_frame_selects_symbol_from_yahoo_multiindex():
    index = pd.date_range("2026-10-01", periods=1, freq="B")
    columns = pd.MultiIndex.from_product(
        [["ABC", "XYZ"], ["Open", "High", "Low", "Close", "Volume"]]
    )
    source = pd.DataFrame([[1, 2, 0.5, 1.5, 100, 2, 3, 1, 2.5, 200]], index=index, columns=columns)
    result = _to_frame(source, "XYZ")
    assert len(result) == 1
    assert result.iloc[0]["종가"] == 2.5
    assert result.iloc[0]["거래대금"] == 500.0
