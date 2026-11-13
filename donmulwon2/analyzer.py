"""Stock screening and market bulletin assembly."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from pykrx import stock

from .indicators import calculate_indicators, latest_signal
from .market_data import DataResult, KrxDataProvider
from .storage import AnalysisStore


class DonmulwonAnalyzer:
    def __init__(self, provider: KrxDataProvider | None = None, store: AnalysisStore | None = None):
        self.provider = provider or KrxDataProvider()
        self.store = store or AnalysisStore()

    def analyze_ticker(self, ticker: str) -> DataResult:
        history = self.provider.ticker_history(ticker, days=420)
        if not history.ok:
            return history
        frame = calculate_indicators(history.data)
        signal = latest_signal(history.data)
        date = frame.index[-1].strftime("%Y%m%d")
        name = self.provider.ticker_name(ticker)
        result = {
            "ticker": ticker,
            "name": name,
            "trading_date": date,
            "signal": signal,
            "matched": bool(signal.get("matched")),
            "latest": {
                "close": int(frame.iloc[-1]["종가"]),
                "change_pct": float(frame.iloc[-1].get("등락률", 0)),
                "volume": int(frame.iloc[-1].get("거래량", 0)),
                "ma10": _number(frame.iloc[-1].get("MA10")),
                "ma20": _number(frame.iloc[-1].get("MA20")),
                "ma60": _number(frame.iloc[-1].get("MA60")),
                "ma240": _number(frame.iloc[-1].get("MA240")),
                "rsi10": _number(frame.iloc[-1].get("RSI10")),
                "rsi14": _number(frame.iloc[-1].get("RSI14")),
                "macd": _number(frame.iloc[-1].get("MACD")),
                "macd_signal": _number(frame.iloc[-1].get("MACD_SIGNAL")),
                "macd_hist": _number(frame.iloc[-1].get("MACD_HIST")),
                "bb_upper": _number(frame.iloc[-1].get("BB_UPPER")),
                "bb_middle": _number(frame.iloc[-1].get("BB_MIDDLE")),
                "bb_lower": _number(frame.iloc[-1].get("BB_LOWER")),
            },
            "ohlcv": frame.tail(260).reset_index().rename(columns={frame.index.name or "날짜": "date"}).to_dict("records"),
        }
        self.store.save_analysis(ticker, name, date, result)
        return DataResult(True, result, "분석 완료")

    def market_bulletin(self, market: str) -> DataResult:
        breadth = self.provider.market_breadth(market)
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
        data["one_line_summary"] = (
            f'{market} {data["date"]}: {tone} '
            f'(상승 {adv} / 하락 {dec}), 거래대금 '
            f'{data["trading_value"]:,}원'
        )
        self.store.save_bulletin(data["date"], market, data)
        return DataResult(True, data, "시장 게시판 갱신")

    def scan_market(
        self,
        market: str,
        progress: Callable[[int, int, str], None] | None = None,
        limit: int | None = None,
    ) -> DataResult:
        """Scan every listed ticker by default; limit is useful for a short trial run."""
        try:
            date = self.provider.latest_trading_date()
            tickers = stock.get_market_ticker_list(date, market=market)
            if limit:
                tickers = tickers[:limit]
            matches, errors = [], []
            total = len(tickers)
            for index, ticker in enumerate(tickers, start=1):
                result = self.analyze_ticker(ticker)
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


def _number(value):
    try:
        if value is None:
            return None
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None
