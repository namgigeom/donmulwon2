"""Stock screening and market bulletin assembly."""
from __future__ import annotations

from typing import Callable
import math

import pandas as pd
from pykrx import stock

from .indicators import calculate_indicators, latest_signal, resample_weekly_ohlcv
from .market_data import DataResult, KrxDataProvider
from .storage import AnalysisStore


class DonmulwonAnalyzer:
    def __init__(self, provider: KrxDataProvider | None = None, store: AnalysisStore | None = None):
        self.provider = provider or KrxDataProvider()
        self.store = store or AnalysisStore()

    def analyze_ticker(
        self, ticker: str, *, name: str | None = None,
        save: bool = True, include_ohlcv: bool = True, use_toss: bool = True
    ) -> DataResult:
        history = self.provider.ticker_history(ticker, days=420, use_toss=use_toss)
        if not history.ok:
            return history
        frame = calculate_indicators(history.data)
        if frame.empty:
            return DataResult(False, message="지표 계산 결과가 비어 있습니다.")
        signal = latest_signal(history.data)
        weekly_frame = resample_weekly_ohlcv(history.data)
        weekly_indicators = calculate_indicators(weekly_frame)
        weekly_summary = _weekly_summary(weekly_indicators)
        date = frame.index[-1].strftime("%Y%m%d")
        name = name or self.provider.ticker_name(ticker)
        last = frame.iloc[-1]
        previous = frame.iloc[-2] if len(frame) > 1 else last
        close = _number(last.get("종가"))
        prev_close = _number(previous.get("종가"))
        change_pct = ((close / prev_close) - 1) * 100 if close and prev_close else None
        result = {
            "ticker": ticker,
            "name": name,
            "trading_date": date,
            "signal": signal,
            "matched": bool(signal.get("matched")),
            "weekly": weekly_summary,
            "weekly_ohlcv": _frame_records(weekly_indicators.tail(52)),
            "latest": {
                "close": _int(last.get("종가")),
                "change_pct": change_pct,
                "volume": _int(last.get("거래량")),
                "ma10": _number(last.get("MA10")),
                "ma20": _number(last.get("MA20")),
                "ma60": _number(last.get("MA60")),
                "ma120": _number(last.get("MA120")),
                "ma240": _number(last.get("MA240")),
                "rsi10": _number(last.get("RSI10")),
                "rsi14": _number(last.get("RSI14")),
                "macd": _number(last.get("MACD")),
                "macd_signal": _number(last.get("MACD_SIGNAL")),
                "macd_hist": _number(last.get("MACD_HIST")),
                "bb_upper": _number(last.get("BB_UPPER")),
                "bb_middle": _number(last.get("BB_MIDDLE")),
                "bb_lower": _number(last.get("BB_LOWER")),
                "volume_ma20": _number(last.get("VOLUME_MA20")),
                "volume_ratio": _number(last.get("거래량")) / _number(last.get("VOLUME_MA20"))
                    if _number(last.get("거래량")) is not None and _number(last.get("VOLUME_MA20")) else None,
                "atr14": _number(last.get("ATR14")),
                "support20": _number(last.get("LOW20")),
                "resistance20": _number(last.get("HIGH20")),
                "high252": _number(last.get("HIGH252")),
                "drawdown52w_pct": (
                    (close / _number(last.get("HIGH252")) - 1) * 100
                    if close and _number(last.get("HIGH252")) else None
                ),
            },
        }
        if include_ohlcv:
            result["ohlcv"] = _frame_records(frame.tail(260))
        if save:
            self.store.save_analysis(ticker, name, date, result)
        return DataResult(True, result, "분석 완료")

    def market_bulletin(self, market: str, date: str | None = None) -> DataResult:
        breadth = self.provider.market_breadth(market, date)
        if not breadth.ok:
            return breadth
        flows = self.provider.investor_flows(market, breadth.data["date"])
        data = dict(breadth.data)
        data["investor_flows"] = flows.data if flows.ok else None
        data["flow_status"] = flows.message
        adv, dec = data["advancers"], data["decliners"]
        if adv > dec:
            tone = "상승 종목 우세"
        elif adv < dec:
            tone = "하락 종목 우세"
        else:
            tone = "상승·하락 종목 비슷"
        flow_values = (data.get("investor_flows") or {}).get("values", {})
        flow_parts = []
        for investor in ("외국인", "개인"):
            if investor in flow_values:
                flow_parts.append(
                    f'{investor} {flow_values[investor] / 100_000_000:+.0f}억'
                )
        flow_summary = ", ".join(flow_parts)
        data["one_line_summary"] = (
            f'{market}: {tone} (상승 {adv:,} / 하락 {dec:,}), '
            f'거래대금 {data["trading_value"]:,}원'
            + (f', {flow_summary}' if flow_summary else '')
        )
        self.store.save_bulletin(data["date"], market, data)
        return DataResult(True, data, "시장 게시판 갱신")

    def scan_market(
        self,
        market: str,
        progress: Callable[[int, int, str], None] | None = None,
        limit: int | None = None,
    ) -> DataResult:
        try:
            date = self.provider.latest_trading_date()
            tickers = stock.get_market_ticker_list(date, market=market)
            try:
                names = stock.get_market_ticker_and_name(date, market=market).to_dict()
            except Exception:
                names = {}
            if limit is not None:
                tickers = tickers[:limit]
            matches, errors = [], []
            total = len(tickers)
            for index, ticker in enumerate(tickers, start=1):
                result = self.analyze_ticker(
                    ticker, name=names.get(ticker), save=False, include_ohlcv=False, use_toss=False
                )
                if result.ok and result.data["matched"]:
                    matches.append(result.data)
                elif not result.ok:
                    errors.append({"ticker": ticker, "error": result.message})
                if progress:
                    progress(index, total, ticker)
            return DataResult(True, {
                "market": market, "date": date, "scanned": total,
                "matches": matches, "error_count": len(errors), "errors": errors[:30],
            }, "종목 검색 완료")
        except Exception as exc:
            return DataResult(False, message=f"시장 종목 검색 실패: {exc}")



def _weekly_summary(frame: pd.DataFrame) -> dict:
    """Summarize the last completed weekly candle as context, not a scan filter."""
    if frame is None or frame.empty:
        return {"ready": False, "reason": "완료된 주봉 데이터가 부족합니다."}
    current = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) > 1 else current

    def value(key):
        return _number(current.get(key))

    close, ma10, ma20 = value("종가"), value("MA10"), value("MA20")
    rsi10, rsi14 = value("RSI10"), value("RSI14")
    macd, macd_signal = value("MACD"), value("MACD_SIGNAL")
    if any(item is None for item in (close, ma10, ma20, rsi10, rsi14, macd, macd_signal)):
        return {
            "ready": False,
            "reason": "주봉 지표 계산을 위한 완료된 주간 데이터가 더 필요합니다.",
            "bars": len(frame),
        }
    if close > ma10 and ma10 > ma20:
        trend = "상승 우위"
    elif close < ma10 and ma10 < ma20:
        trend = "하락 압력"
    else:
        trend = "혼조"
    return {
        "ready": True,
        "date": frame.index[-1].strftime("%Y-%m-%d"),
        "bars": len(frame),
        "trend": trend,
        "close": _int(close),
        "ma10": ma10,
        "ma20": ma20,
        "above_ma10": bool(close > ma10),
        "above_ma20": bool(close > ma20),
        "rsi10": rsi10,
        "rsi14": rsi14,
        "rsi10_rising": bool(rsi10 > _number(previous.get("RSI10"))) if _number(previous.get("RSI10")) is not None else None,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_bullish": bool(macd > macd_signal),
    }


def _number(value):
    try:
        if value is None or pd.isna(value):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _int(value):
    number = _number(value)
    return int(number) if number is not None else None


def _frame_records(frame):
    rows = []
    for index, row in frame.iterrows():
        item = {"date": index.strftime("%Y-%m-%d") if hasattr(index, "strftime") else str(index)}
        for key, value in row.items():
            item[str(key)] = _number(value)
        rows.append(item)
    return rows
