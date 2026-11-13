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


def _statement_metric(frame: pd.DataFrame | None, aliases: tuple[str, ...]) -> float | None:
    if frame is None or frame.empty:
        return None
    for alias in aliases:
        if alias in frame.index:
            try:
                value = pd.to_numeric(frame.loc[alias].iloc[0], errors="coerce")
                return float(value) if pd.notna(value) else None
            except (TypeError, ValueError, IndexError):
                continue
    return None


def _company_profile_from_data(symbol: str, info: dict, annual: pd.DataFrame | None,
                               quarterly: pd.DataFrame | None, current_price: float | None) -> dict:
    def period(frame):
        if frame is None or frame.empty or len(frame.columns) == 0:
            return None
        col = frame.columns[0]
        return str(col.date() if hasattr(col, "date") else col)[:10]

    def metrics(frame):
        return {
            "period": period(frame),
            "revenue": _statement_metric(frame, ("Total Revenue", "Operating Revenue", "Revenue")),
            "operating_income": _statement_metric(frame, ("Operating Income", "Operating Income Loss")),
            "net_income": _statement_metric(frame, ("Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations")),
        }

    annual_latest = metrics(annual)
    annual_previous = metrics(annual.iloc[:, 1:]) if annual is not None and len(annual.columns) > 1 else None
    revenue_growth = None
    if annual_latest and annual_previous:
        current_revenue, previous_revenue = annual_latest["revenue"], annual_previous["revenue"]
        if current_revenue is not None and previous_revenue not in (None, 0):
            revenue_growth = round((current_revenue / previous_revenue - 1) * 100, 2)
    target = info.get("targetMeanPrice")
    target = float(target) if isinstance(target, (int, float)) else None
    analyst_count = info.get("numberOfAnalystOpinions")
    analyst_count = int(analyst_count) if isinstance(analyst_count, (int, float)) else None
    return {
        "available": bool(info.get("longBusinessSummary") or info.get("sector") or annual_latest),
        "source": "Yahoo Finance",
        "symbol": symbol,
        "currency": info.get("currency") or "KRW",
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "website": info.get("website"),
        "employees": info.get("fullTimeEmployees"),
        "market_cap": info.get("marketCap"),
        "summary": info.get("longBusinessSummary"),
        "annual": ({**annual_latest, "revenue_growth_pct": revenue_growth} if annual_latest else None),
        "quarterly": metrics(quarterly) if quarterly is not None and not quarterly.empty else None,
        "outlook": {
            "rating": info.get("recommendationKey"),
            "target_mean_price": target,
            "target_upside_pct": round((target / current_price - 1) * 100, 2)
                if target is not None and current_price not in (None, 0) else None,
            "analyst_count": analyst_count,
        },
    }


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

    def index_snapshot(self, market: str, date: str | None = None) -> DataResult:
        """Return the latest index close, daily move and a short close-price sparkline."""
        try:
            day = date or self.latest_trading_date()
            index_code = {"KOSPI": "1001", "KOSDAQ": "2001"}[market.upper()]
            end = datetime.strptime(day, "%Y%m%d")
            start = end - timedelta(days=18)
            frame = stock.get_index_ohlcv_by_date(
                start.strftime("%Y%m%d"), day, index_code, name_display=False,
            )
            if frame is None or frame.empty or "종가" not in frame.columns:
                return DataResult(False, message=f"{market} 지수 종가 데이터가 비어 있습니다.")
            closes = pd.to_numeric(frame["종가"], errors="coerce").dropna()
            if closes.empty:
                return DataResult(False, message=f"{market} 지수 종가를 확인할 수 없습니다.")
            current = float(closes.iloc[-1])
            previous = float(closes.iloc[-2]) if len(closes) > 1 else current
            change = current - previous
            change_pct = (change / previous * 100) if previous else 0.0
            return DataResult(True, {
                "name": market, "close": current, "change": change,
                "change_pct": change_pct, "trend": [float(value) for value in closes.tail(7)],
            }, "KRX 지수 종가")
        except Exception as exc:
            return DataResult(False, message=f"{market} 지수 조회 실패: {exc}")

    def sector_performance(self, market: str, date: str | None = None) -> DataResult:
        """Aggregate constituent returns by KRX industry classification."""
        try:
            day = date or self.latest_trading_date()
            frame = stock.get_market_sector_classifications(day, market=market.upper())
            required = {"업종명", "등락률"}
            if frame is None or frame.empty or not required.issubset(frame.columns):
                return DataResult(False, message=f"{market} 업종별 등락 데이터가 비어 있거나 형식이 다릅니다.")
            work = frame[["업종명", "등락률"]].copy()
            work["등락률"] = pd.to_numeric(work["등락률"], errors="coerce")
            work = work.dropna(subset=["업종명", "등락률"])
            grouped = work.groupby("업종명")["등락률"].agg(["mean", "count"]).reset_index()
            sectors = [
                {"name": str(row["업종명"]), "change_pct": round(float(row["mean"]), 2),
                 "stock_count": int(row["count"]), "market": market.upper()}
                for _, row in grouped.iterrows()
            ]
            return DataResult(True, sectors, "KRX 업종 구성 종목 평균 등락률")
        except Exception as exc:
            return DataResult(False, message=f"{market} 업종별 등락 수집 실패: {exc}")

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

    def company_profile(self, ticker: str, current_price: float | None = None) -> DataResult:
        """Fetch optional company description, reported statements and analyst consensus from Yahoo Finance."""
        try:
            import yfinance as yf
            last_error = ""
            for suffix in (".KS", ".KQ"):
                symbol = ticker + suffix
                try:
                    item = yf.Ticker(symbol)
                    info = item.info or {}
                    try:
                        annual = item.financials
                    except Exception:
                        annual = None
                    try:
                        quarterly = item.quarterly_financials
                    except Exception:
                        quarterly = None
                    profile = _company_profile_from_data(symbol, info, annual, quarterly, current_price)
                    if profile["available"]:
                        return DataResult(True, profile, "Yahoo Finance 기업·재무 데이터")
                except Exception as exc:
                    last_error = str(exc)
            return DataResult(False, message=(
                "Yahoo Finance에서 기업 개요·재무제표를 확인하지 못했습니다."
                + (f" ({last_error[:180]})" if last_error else "")
            ))
        except ImportError:
            return DataResult(False, message="기업 재무정보 모듈(yfinance)이 설치되지 않았습니다.")

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
