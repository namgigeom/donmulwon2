"""KRX market data adapter. Failed requests are surfaced; no sample quotes are generated."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import os

import pandas as pd
from pykrx import stock

from .toss_api import TossApiError, TossClient


@dataclass
class DataResult:
    ok: bool
    data: Any = None
    message: str = ""


class KrxDataProvider:
    def __init__(self):
        self.last_error = ""
        self.toss = TossClient()

    @staticmethod
    def _date(value: datetime | None = None) -> str:
        return (value or datetime.now()).strftime("%Y%m%d")

    @staticmethod
    def latest_trading_date(max_days: int = 14) -> str:
        end = datetime.now()
        start = end - timedelta(days=max(max_days, 30))
        try:
            frame = stock.get_index_ohlcv_by_date(
                start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), "1001",
                name_display=False,
            )
            if frame is not None and not frame.empty:
                return frame.index[-1].strftime("%Y%m%d")
        except Exception as exc:
            detail = str(exc)
            if "Expecting value" in detail and not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
                raise RuntimeError(
                    "KRX 서버가 정상 JSON 대신 빈 응답/오류 응답을 반환했습니다. "
                    "최근 pykrx의 인증 필요 API는 KRX 회원 인증이 필요할 수 있습니다. "
                    "저장소 루트 .env에 KRX_ID와 KRX_PW를 설정하고 백엔드를 재시작하세요. "
                    "인증정보가 이미 설정되어 있다면 KRX 서버 장애 또는 접속 제한 가능성이 있습니다."
                ) from exc
            raise RuntimeError(f"KRX 최근 거래일 조회 실패: {exc}") from exc
        raise RuntimeError("최근 거래일을 확인하지 못했습니다. KRX 응답을 확인하세요.")

    def index_history(self, index_code: str, days: int = 90) -> DataResult:
        try:
            end = datetime.now()
            start = end - timedelta(days=days * 2)
            frame = stock.get_index_ohlcv_by_date(
                start.strftime("%Y%m%d"), self._date(end), index_code,
                name_display=False,
            )
            if frame is None or frame.empty:
                return DataResult(False, message="지수 데이터를 받지 못했습니다.")
            return DataResult(True, frame, "KRX 지수 데이터")
        except Exception as exc:
            detail = str(exc)
            if "Expecting value" in detail and not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
                detail = (
                    "KRX 응답이 JSON이 아닙니다. .env에 KRX_ID와 KRX_PW를 설정하고 "
                    "백엔드를 재시작하세요. 인증정보가 이미 있으면 KRX 서버 장애/접속 제한일 수 있습니다."
                )
            return DataResult(False, message=f"지수 데이터 수집 실패: {detail}")

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
            frame = stock.get_market_trading_value_by_investor(day, day, market,
                                                               etf=True, etn=True, elw=True)
            if frame is None or frame.empty:
                return DataResult(False, message="투자자별 거래대금 데이터를 받지 못했습니다.")
            if "순매수" not in frame.columns:
                return DataResult(False, message="투자자별 순매수 컬럼을 확인할 수 없습니다.")
            net = pd.to_numeric(frame["순매수"], errors="coerce").fillna(0)
            values = {str(investor): int(amount) for investor, amount in net.items()}
            return DataResult(True, {"date": day, "market": market, "values": values},
                              "KRX 투자자별 거래대금 순매수")
        except Exception as exc:
            return DataResult(False, message=f"투자자별 수급 수집 실패: {exc}")

    def ticker_history(self, ticker: str, days: int = 420, *, use_toss: bool = True) -> DataResult:
        if use_toss and self.toss.configured:
            try:
                rows = self.toss.candles(ticker, count=min(days, 600))
                if not rows:
                    return DataResult(False, message=f"Toss API에서 {ticker} 일봉을 받지 못했습니다.")
                frame = pd.DataFrame(rows)
                aliases = {
                    "timestamp": "date", "openPrice": "시가", "highPrice": "고가",
                    "lowPrice": "저가", "closePrice": "종가", "volume": "거래량",
                }
                frame = frame.rename(columns=aliases)
                required = ["date", "시가", "고가", "저가", "종가", "거래량"]
                missing = [key for key in required if key not in frame.columns]
                if missing:
                    return DataResult(False, message=f"Toss 캔들 응답 필드 누락: {', '.join(missing)}")
                frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
                frame = frame.dropna(subset=["date"]).set_index("date").sort_index()
                for key in ["시가", "고가", "저가", "종가", "거래량"]:
                    frame[key] = pd.to_numeric(frame[key], errors="coerce")
                frame = frame.dropna(subset=["시가", "고가", "저가", "종가"])
                if frame.empty:
                    return DataResult(False, message="Toss 캔들 데이터가 비어 있거나 숫자로 변환되지 않습니다.")
                return DataResult(True, frame, "Toss Securities Open API 일봉")
            except TossApiError as exc:
                return DataResult(False, message=str(exc))
            except Exception as exc:
                return DataResult(False, message=f"Toss {ticker} 일봉 변환 실패: {exc}")
        try:
            end = datetime.now()
            start = end - timedelta(days=int(days * 1.7))
            frame = stock.get_market_ohlcv_by_date(
                start.strftime("%Y%m%d"), self._date(end), ticker
            )
            if frame is None or frame.empty:
                return DataResult(False, message=f"{ticker} 일봉 데이터를 받지 못했습니다.")
            return DataResult(True, frame, "KRX(pykrx) 일봉 데이터 - Toss 미설정")
        except Exception as exc:
            return DataResult(False, message=f"{ticker} 데이터 수집 실패: {exc}")

    def ticker_name(self, ticker: str, date: str | None = None) -> str:
        if self.toss.configured:
            try:
                info = self.toss.stock_info(ticker)
                return str(info.get("name") or info.get("stockName") or info.get("displayName") or ticker)
            except Exception:
                pass
        try:
            return stock.get_market_ticker_name(ticker)
        except Exception:
            return ticker
