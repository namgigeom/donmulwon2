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
        company_loader = getattr(self.provider, "company_profile", None)
        company_result = (
            company_loader(ticker, current_price=close)
            if include_ohlcv and callable(company_loader)
            else DataResult(False, message="기업 정보 조회는 개별 종목 분석에서만 실행합니다.")
        )
        result = {
            "ticker": ticker,
            "name": name,
            "trading_date": date,
            "company": company_result.data if company_result.ok else {
                "available": False, "source": "Yahoo Finance", "message": company_result.message
            },
            "signal": signal,
            "matched": bool(signal.get("matched")),
            "weekly": weekly_summary,
            "weekly_ohlcv": _frame_records(weekly_indicators.tail(52)),
            "latest": {
                "close": _int(last.get("종가")),
                "change_pct": change_pct,
                "volume": _int(last.get("거래량")),
                "trading_value": _number(last.get("거래대금")) ?? (close is not None and _number(last.get("거래량")) is not None ? close * _number(last.get("거래량")) : None),
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
                "volume_ma10": _number(last.get("VOLUME_MA10")),
                "volume_ratio": _number(last.get("거래량")) / _number(last.get("VOLUME_MA10"))
                    if _number(last.get("거래량")) is not None and _number(last.get("VOLUME_MA10")) else None,
                "atr14": _number(last.get("ATR14")),
                "support20": _number(last.get("LOW20")),
                "resistance20": _number(last.get("HIGH20")),
                "high252": _number(last.get("HIGH252")),
                "drawdown52w_pct": (
                    (close / _number(last.get("HIGH252")) - 1) * 100
                    if close and _number(last.get("HIGH252")) else None
                ),
                "trade_plan": _trade_plan(close, _number(last.get("ATR14"))),
            },
        }
        if include_ohlcv:
            result["ohlcv"] = _frame_records(frame.tail(130))
        if save:
            self.store.save_analysis(ticker, name, date, result)
        return DataResult(True, result, "분석 완료")

    def market_bulletin(self, market: str, date: str | None = None) -> DataResult:
        breadth = self.provider.market_breadth(market, date)
        if not breadth.ok:
            return breadth
        flows = self.provider.investor_flows(market, breadth.data["date"])
        data = dict(breadth.data)
        index = self.provider.index_snapshot(market, data["date"])
        sectors = self.provider.sector_performance(market, data["date"])
        data["index"] = index.data if index.ok else None
        data["sectors"] = sectors.data if sectors.ok else []
        data["sector_status"] = sectors.message
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
            markets = ("KOSPI", "KOSDAQ") if market.upper() == "ALL" else (market.upper(),)
            ticker_names: dict[str, str] = {}
            for selected_market in markets:
                listed = stock.get_market_ticker_list(date, market=selected_market)
                try:
                    ticker_names.update(stock.get_market_ticker_and_name(date, market=selected_market).to_dict())
                except Exception:
                    pass
                for ticker in listed:
                    ticker_names.setdefault(ticker, "")
            tickers = list(ticker_names)
            if limit is not None:
                tickers = tickers[:limit]
            matches, errors = [], []
            total = len(tickers)
            for index, ticker in enumerate(tickers, start=1):
                result = self.analyze_ticker(
                    ticker, name=ticker_names.get(ticker) or None, save=False,
                    include_ohlcv=False, use_toss=False
                )
                if result.ok and result.data["matched"]:
                    latest = result.data.get("latest", {})
                    close, ma240 = latest.get("close"), latest.get("ma240")
                    trading_value = latest.get("trading_value")
                    if ma240 is None or close is None:
                        errors.append({
                            "ticker": ticker,
                            "error": "종가 또는 MA240 데이터가 없어 240일선 필터 판정 불가",
                        })
                    elif trading_value is None:
                        errors.append({
                            "ticker": ticker,
                            "error": "당일 거래대금 데이터가 없어 500만원 필터 판정 불가",
                        })
                    elif close >= ma240 and trading_value >= 5_000_000:
                        matches.append(result.data)
                    # 240일선 아래 또는 당일 거래대금 500만원 미만이면 후보에서 제외한다.
                elif not result.ok:
                    errors.append({"ticker": ticker, "error": result.message})
                if progress:
                    progress(index, total, ticker)
            grade_order = {"A": 0, "B": 1, "C": 2}
            matches.sort(key=lambda item: (
                grade_order.get((item.get("weekly") or {}).get("grade", "C"), 2),
                -((item.get("weekly") or {}).get("grade_score") or 0),
                -((item.get("latest") or {}).get("volume_ratio") or 0),
            ))
            grade_counts = {
                grade: sum(1 for item in matches if (item.get("weekly") or {}).get("grade", "C") == grade)
                for grade in ("A", "B", "C")
            }
            return DataResult(True, {
                "market": market.upper(), "date": date, "scanned": total,
                "matches": matches, "grade_counts": grade_counts,
                "error_count": len(errors), "errors": errors[:30],
            }, "종목 검색 완료")
        except Exception as exc:
            return DataResult(False, message=f"시장 종목 검색 실패: {exc}")




def _trade_plan(close: float | None, atr: float | None) -> dict:
    """Create transparent ATR-based reference levels, never a guaranteed trade recommendation."""
    if close is None or atr is None or close <= 0 or atr <= 0:
        return {"ready": False, "reason": "ATR/종가 데이터가 부족해 기준 가격을 계산할 수 없습니다."}
    entry_low = close - atr * 0.30
    entry_high = close + atr * 0.20
    stop = close - atr * 1.50
    risk = entry_high - stop
    return {
        "ready": True,
        "method": "최근 종가와 ATR(14) 기반 참고값",
        "entry_low": round(entry_low, 2),
        "entry_high": round(entry_high, 2),
        "stop_loss": round(stop, 2),
        "target_1": round(entry_high + risk * 2, 2),
        "target_2": round(entry_high + risk * 3, 2),
        "risk_per_share": round(risk, 2),
        "reward_risk_1": 2.0,
        "reward_risk_2": 3.0,
        "warning": "가격 변동성 기반 참고 구간이며 갭·유동성·시장 급변 시 손실은 기준을 초과할 수 있습니다.",
    }


def _weekly_summary(frame: pd.DataFrame) -> dict:
    """Summarize the last completed weekly candle as context, not a scan filter."""
    if frame is None or frame.empty:
        return {
            "ready": False, "reason": "완료된 주봉 데이터가 부족합니다.",
            "trend": "데이터 부족", "grade": "C", "grade_score": 0,
            "grade_reason": "주봉 데이터 부족으로 추세 확인 불가",
        }
    current = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) > 1 else current

    def value(key):
        return _number(current.get(key))

    def previous_value(key):
        return _number(previous.get(key))

    close, ma10, ma20 = value("종가"), value("MA10"), value("MA20")
    prev_ma10, prev_ma20 = previous_value("MA10"), previous_value("MA20")
    rsi10, rsi14 = value("RSI10"), value("RSI14")
    macd, macd_signal = value("MACD"), value("MACD_SIGNAL")
    if any(item is None for item in (close, ma10, ma20, rsi10, rsi14, macd, macd_signal)):
        return {
            "ready": False,
            "reason": "주봉 지표 계산을 위한 완료된 주간 데이터가 더 필요합니다.",
            "bars": len(frame), "trend": "데이터 부족", "grade": "C",
            "grade_score": 0, "grade_reason": "주봉 지표 부족으로 추세 확인 불가",
        }

    above_ma10 = close > ma10
    above_ma20 = close > ma20
    ma10_above_ma20 = ma10 > ma20
    ma10_rising = prev_ma10 is not None and ma10 > prev_ma10
    ma20_rising = prev_ma20 is not None and ma20 > prev_ma20
    macd_bullish = macd > macd_signal
    rsi_bullish = rsi10 > rsi14

    # Weekly trend is a grading input, not a hard exclusion. A weak trend
    # remains visible as C so the user can distinguish it from a strong setup.
    score = (
        (20 if above_ma10 else 0)
        + (15 if above_ma20 else 0)
        + (20 if ma10_above_ma20 else 0)
        + (15 if ma10_rising else 0)
        + (10 if ma20_rising else 0)
        + (15 if macd_bullish else 0)
        + (5 if rsi_bullish else 0)
    )
    grade = "A" if score >= 80 else "B" if score >= 55 else "C"
    trend = {
        "A": "강한 상승 추세",
        "B": "상승 전환·완만한 상승",
        "C": "혼조·하락 추세",
    }[grade]
    reasons = []
    for condition, label in (
        (above_ma10, "주봉 종가 MA10 상회"),
        (above_ma20, "주봉 종가 MA20 상회"),
        (ma10_above_ma20, "MA10/20 정배열"),
        (ma10_rising, "주봉 MA10 상승"),
        (ma20_rising, "주봉 MA20 상승"),
        (macd_bullish, "주봉 MACD 강세"),
        (rsi_bullish, "RSI10 우위"),
    ):
        if condition:
            reasons.append(label)
    return {
        "ready": True,
        "date": frame.index[-1].strftime("%Y-%m-%d"),
        "bars": len(frame),
        "trend": trend,
        "grade": grade,
        "grade_score": score,
        "grade_reason": " · ".join(reasons) if reasons else "주봉 상승 조건 미충족",
        "close": _int(close),
        "ma10": ma10,
        "ma20": ma20,
        "above_ma10": above_ma10,
        "above_ma20": above_ma20,
        "ma10_above_ma20": ma10_above_ma20,
        "ma10_rising": ma10_rising,
        "ma20_rising": ma20_rising,
        "rsi10": rsi10,
        "rsi14": rsi14,
        "rsi10_rising": bool(rsi10 > previous_value("RSI10")) if previous_value("RSI10") is not None else None,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_bullish": macd_bullish,
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
