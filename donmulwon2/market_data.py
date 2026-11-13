"""KRX market data adapter. Failed requests are surfaced; no sample quotes are generated."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from pykrx import stock


@dataclass
class DataResult:
    ok: bool
    data: Any = None
    message: str = ""


class KrxDataProvider:
    def __init__(self):
        self.last_error = ""

    @staticmethod
    def _date(value: datetime | None = None) -> str:
        return (value or datetime.now()).strftime("%Y%m%d")

    @staticmethod
    def latest_trading_date(max_days: int = 14) -> str:
        today = datetime.now()
        for offset in range(max_days + 1):
            candidate = (today - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                tickers = stock.get_market_ticker_list(candidate, market="KOSPI")
                if tickers:
                    return candidate
            except Exception:
                continue
        raise RuntimeError("최근 거래일을 확인하지 못했습니다. KRX 응답을 확인하세요.")

    def index_history(self, index_code: str, days: int = 90) -> DataResult:
        try:
            end = datetime.now()
            start = end - timedelta(days=days * 2)
            frame = stock.get_index_ohlcv_by_date(
                start.strftime("%Y%m%d"), self._date(end), index_code
            )
            if frame is None or frame.empty:
                return DataResult(False, message="지수 데이터를 받지 못했습니다.")
            return DataResult(True, frame, "KRX 지수 데이터")
        except Exception as exc:
            return DataResult(False, message=f"지수 데이터 수집 실패: {exc}")

    def market_breadth(self, market: str, date: str | None = None) -> DataResult:
        try:
            day = date or self.latest_trading_date()
            frame = stock.get_market_ohlcv_by_ticker(day, market=market)
            if frame is None or frame.empty:
                return DataResult(False, message=f"{market} 등락 데이터가 비어 있습니다.")
            change = pd.to_numeric(frame["등락률"], errors="coerce")
            data = {
                "date": day,
                "market": market,
                "advancers": int((change > 0).sum()),
                "decliners": int((change < 0).sum()),
                "unchanged": int((change == 0).sum()),
                "ticker_count": int(change.notna().sum()),
                "trading_value": int(pd.to_numeric(frame["거래대금"], errors="coerce").fillna(0).sum()),
            }
            return DataResult(True, data, "KRX 전 종목 등락 및 거래대금")
        except Exception as exc:
            return DataResult(False, message=f"{market} 시장 통계 수집 실패: {exc}")

    def investor_flows(self, market: str, date: str | None = None) -> DataResult:
        try:
            day = date or self.latest_trading_date()
            frame = stock.get_market_trading_value_by_date(day, day, market)
            if frame is None or frame.empty:
                return DataResult(False, message="투자자별 거래대금 데이터를 받지 못했습니다.")
            row = frame.iloc[-1]
            values = {str(key): int(value) for key, value in row.items() if pd.notna(value)}
            return DataResult(True, {"date": day, "market": market, "values": values}, "KRX 투자자별 거래대금")
        except Exception as exc:
            return DataResult(False, message=f"투자자별 수급 수집 실패: {exc}")

    def ticker_history(self, ticker: str, days: int = 420) -> DataResult:
        try:
            end = datetime.now()
            start = end - timedelta(days=int(days * 1.7))
            frame = stock.get_market_ohlcv_by_date(
                start.strftime("%Y%m%d"), self._date(end), ticker
            )
            if frame is None or frame.empty:
                return DataResult(False, message=f"{ticker} 일봉 데이터를 받지 못했습니다.")
            return DataResult(True, frame, "KRX 일봉 데이터")
        except Exception as exc:
            return DataResult(False, message=f"{ticker} 데이터 수집 실패: {exc}")

    def ticker_name(self, ticker: str, date: str | None = None) -> str:
        try:
            return stock.get_market_ticker_name(ticker)
        except Exception:
            return ticker
