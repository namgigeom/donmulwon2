"""US market bulletin from Yahoo Finance: Nasdaq/S&P 500, NYSE+NASDAQ breadth and sector ETFs."""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo
import threading
import time as time_module

import pandas as pd

_CACHE = None
_CACHE_AT = 0.0
_LOCK = threading.Lock()
_SECTOR_ETFS = {
    "XLB": "소재", "XLC": "커뮤니케이션 서비스", "XLE": "에너지",
    "XLF": "금융", "XLI": "산업재", "XLK": "정보기술",
    "XLP": "필수소비재", "XLRE": "부동산", "XLU": "유틸리티",
    "XLV": "헬스케어", "XLY": "임의소비재",
}


def _last_completed_us_date() -> pd.Timestamp:
    now = datetime.now(ZoneInfo("America/New_York"))
    day = now.date()
    if now.time() < time(16, 15):
        day = pd.Timestamp(day).date() - pd.Timedelta(days=1)
    return pd.Timestamp(day)


def _history(symbol: str, end_date: pd.Timestamp) -> pd.DataFrame:
    import yfinance as yf
    frame = yf.Ticker(symbol).history(period="10d", interval="1d", auto_adjust=True)
    if frame is None or frame.empty:
        return pd.DataFrame()
    frame = frame.copy()
    idx = pd.to_datetime(frame.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    frame.index = idx.normalize()
    return frame.loc[frame.index <= end_date]


def _index_snapshot(symbol: str, label: str, end_date: pd.Timestamp) -> dict:
    frame = _history(symbol, end_date)
    if frame.empty or "Close" not in frame:
        raise RuntimeError(f"{label} 지수 데이터를 받지 못했습니다.")
    closes = pd.to_numeric(frame["Close"], errors="coerce").dropna()
    if len(closes) < 2:
        raise RuntimeError(f"{label} 지수의 전일 종가 데이터가 부족합니다.")
    close, previous = float(closes.iloc[-1]), float(closes.iloc[-2])
    change = close - previous
    return {
        "name": label, "close": close, "change": change,
        "change_pct": change / previous * 100 if previous else 0.0,
        "trend": [float(value) for value in closes.tail(7)],
        "date": closes.index[-1].strftime("%Y-%m-%d"),
    }


def _sector_snapshot(end_date: pd.Timestamp) -> list[dict]:
    import yfinance as yf
    symbols = list(_SECTOR_ETFS)
    downloaded = yf.download(
        tickers=symbols, period="10d", interval="1d", group_by="ticker",
        auto_adjust=True, actions=False, threads=True, progress=False, timeout=20,
    )
    from .us_market_scanner import _to_frame
    sectors = []
    for symbol in symbols:
        frame = _to_frame(downloaded, symbol)
        if frame.empty:
            continue
        frame.index = pd.to_datetime(frame.index).normalize()
        frame = frame.loc[frame.index <= end_date]
        if len(frame) < 2:
            continue
        previous, latest = float(frame["종가"].iloc[-2]), float(frame["종가"].iloc[-1])
        if previous:
            sectors.append({
                "name": _SECTOR_ETFS[symbol], "ticker": symbol,
                "change_pct": round((latest / previous - 1) * 100, 2),
                "stock_count": 0, "market": "US",
            })
    return sorted(sectors, key=lambda item: item["change_pct"], reverse=True)


def _breadth_and_turnover(end_date: pd.Timestamp) -> dict:
    import yfinance as yf
    from .us_market_scanner import us_common_stock_universe, _to_frame

    universe = us_common_stock_universe()
    symbols = [symbol.replace(".", "-") for symbol, _ in universe]
    advancers = decliners = unchanged = successful = 0
    trading_value = 0.0
    errors = 0
    for start in range(0, len(symbols), 80):
        batch = symbols[start:start + 80]
        try:
            downloaded = yf.download(
                tickers=batch, period="10d", interval="1d", group_by="ticker",
                auto_adjust=True, actions=False, threads=True, progress=False, timeout=25,
            )
        except Exception:
            errors += len(batch)
            continue
        for symbol in batch:
            frame = _to_frame(downloaded, symbol)
            if frame.empty:
                errors += 1
                continue
            frame.index = pd.to_datetime(frame.index).normalize()
            frame = frame.loc[frame.index <= end_date]
            if len(frame) < 2:
                errors += 1
                continue
            previous = float(frame["종가"].iloc[-2])
            latest = float(frame["종가"].iloc[-1])
            volume = float(frame["거래량"].iloc[-1])
            if previous <= 0:
                errors += 1
                continue
            successful += 1
            if latest > previous:
                advancers += 1
            elif latest < previous:
                decliners += 1
            else:
                unchanged += 1
            trading_value += latest * volume
    if successful == 0:
        raise RuntimeError("NYSE·NASDAQ 구성 종목의 등락 데이터를 받지 못했습니다.")
    return {
        "advancers": advancers, "decliners": decliners, "unchanged": unchanged,
        "ticker_count": successful, "universe_count": len(symbols),
        "trading_value": trading_value, "currency": "USD",
        "coverage_pct": round(successful / max(len(symbols), 1) * 100, 1),
        "error_count": errors,
    }


def us_market_bulletin(force_refresh: bool = False) -> dict:
    """Return a cached daily US market snapshot. All breadth counts use common stocks."""
    global _CACHE, _CACHE_AT
    with _LOCK:
        if _CACHE is not None and not force_refresh and time_module.time() - _CACHE_AT < 1800:
            return dict(_CACHE)
        end_date = _last_completed_us_date()
        nasdaq = _index_snapshot("^IXIC", "NASDAQ 종합", end_date)
        sp500 = _index_snapshot("^GSPC", "S&P 500", end_date)
        breadth = _breadth_and_turnover(end_date)
        sectors = _sector_snapshot(end_date)
        dates = [nasdaq["date"], sp500["date"]]
        result = {
            "market": "US", "date": min(dates), "currency": "USD",
            "indexes": {"nasdaq": nasdaq, "sp500": sp500},
            **breadth, "sectors": sectors, "investor_flows": None,
            "investor_flow_status": "Yahoo Finance 무료 데이터에서 미국 투자자별 순매수 통계 미제공",
            "source": "Yahoo Finance · NasdaqTrader symbol directory",
            "breadth_scope": "NYSE + NASDAQ 보통주",
        }
        result["one_line_summary"] = (
            f"미국 시장: 상승 {breadth['advancers']:,} / 하락 {breadth['decliners']:,}, "
            f"거래대금 ${breadth['trading_value'] / 1_000_000_000:.1f}B"
        )
        _CACHE, _CACHE_AT = result, time_module.time()
        return dict(result)
