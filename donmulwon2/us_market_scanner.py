"""US NYSE/NASDAQ common-stock scanner using Yahoo Finance daily bars."""
from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from urllib.request import Request, urlopen
import re
import threading

import pandas as pd

from .indicators import calculate_indicators, latest_signal, resample_weekly_ohlcv

_UNIVERSE_CACHE = None
_UNIVERSE_LOCK = threading.Lock()
_FX_CACHE = None


def _read_directory(url: str) -> pd.DataFrame:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8", errors="replace")
    raw = raw.split("File Creation Time", 1)[0]
    return pd.read_csv(StringIO(raw), sep="|", dtype=str)


def us_common_stock_universe() -> list[tuple[str, str]]:
    """Return NASDAQ-listed and NYSE-listed common stocks, excluding ETFs/test issues."""
    global _UNIVERSE_CACHE
    with _UNIVERSE_LOCK:
        if _UNIVERSE_CACHE is not None:
            return list(_UNIVERSE_CACHE)
        nasdaq = _read_directory("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt")
        other = _read_directory("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt")
        rows: dict[str, str] = {}
        if {"Symbol", "Security Name", "Test Issue", "ETF"}.issubset(nasdaq.columns):
            selected = nasdaq[
                (nasdaq["Test Issue"] == "N")
                & (nasdaq["ETF"] == "N")
                & (~nasdaq["Symbol"].str.contains(r"[$^]", regex=True, na=False))
            ]
            for _, row in selected.iterrows():
                rows[str(row["Symbol"])] = str(row["Security Name"])
        if {"ACT Symbol", "Security Name", "Exchange", "Test Issue", "ETF"}.issubset(other.columns):
            selected = other[
                (other["Exchange"] == "N")
                & (other["Test Issue"] == "N")
                & (other["ETF"] == "N")
                & (~other["ACT Symbol"].str.contains(r"[$^]", regex=True, na=False))
            ]
            for _, row in selected.iterrows():
                rows[str(row["ACT Symbol"])] = str(row["Security Name"])
        excluded = re.compile(r"\b(warrant|right|unit|preferred|depositary|when issued)\b", re.I)
        _UNIVERSE_CACHE = sorted(
            ((symbol, name) for symbol, name in rows.items() if not excluded.search(name)),
            key=lambda item: item[0],
        )
        if not _UNIVERSE_CACHE:
            raise RuntimeError("NYSE/NASDAQ 종목 목록을 가져오지 못했습니다.")
        return list(_UNIVERSE_CACHE)


def _usdkrw_rate() -> float:
    global _FX_CACHE
    if _FX_CACHE is not None:
        return _FX_CACHE
    import yfinance as yf
    fx = yf.Ticker("KRW=X").history(period="5d", interval="1d", auto_adjust=False)
    if fx is None or fx.empty:
        raise RuntimeError("USD/KRW 환율 데이터를 받지 못했습니다.")
    value = float(fx["Close"].dropna().iloc[-1])
    if not 500 <= value <= 3000:
        raise RuntimeError(f"USD/KRW 환율 값이 비정상적입니다: {value}")
    _FX_CACHE = value
    return value


def _to_frame(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if symbol not in data.columns.get_level_values(0):
            return pd.DataFrame()
        data = data[symbol].copy()
    else:
        data = data.copy()
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(data.columns):
        return pd.DataFrame()
    frame = pd.DataFrame(index=pd.to_datetime(data.index).tz_localize(None))
    frame["시가"] = pd.to_numeric(data["Open"], errors="coerce")
    frame["고가"] = pd.to_numeric(data["High"], errors="coerce")
    frame["저가"] = pd.to_numeric(data["Low"], errors="coerce")
    frame["종가"] = pd.to_numeric(data["Close"], errors="coerce")
    frame["거래량"] = pd.to_numeric(data["Volume"], errors="coerce")
    frame["거래대금"] = frame["종가"] * frame["거래량"]
    return frame.dropna(subset=["종가"]).sort_index()


def scan_us_market(progress=None, limit: int | None = None) -> dict:
    """Scan confirmed daily bars; KRW liquidity thresholds are converted to USD."""
    import yfinance as yf
    from .analyzer import _number, _trade_plan, _weekly_summary

    universe = us_common_stock_universe()
    if limit is not None:
        universe = universe[:limit]
    fx = _usdkrw_rate()
    daily_min_usd = 500_000_000 / fx
    avg20_min_usd = 2_000_000_000 / fx
    symbols = [symbol.replace(".", "-") for symbol, _ in universe]
    names = {symbol.replace(".", "-"): name for symbol, name in universe}
    matches, errors, data_insufficient = [], [], []
    latest_scan_date = None
    stages = {"rsi": 0, "macd": 0, "ma10": 0, "trading_value": 0, "weekly_ma10": 0}
    total = len(symbols)
    # Batch downloads reduce Yahoo requests while keeping memory bounded.
    for start in range(0, total, 40):
        batch = symbols[start:start + 40]
        try:
            downloaded = yf.download(
                tickers=batch, period="2y", interval="1d", group_by="ticker",
                auto_adjust=True, actions=False, threads=True, progress=False,
                timeout=25,
            )
        except Exception as exc:
            errors.extend({"ticker": item, "error": f"Yahoo 데이터 수집 실패: {str(exc)[:140]}"} for item in batch)
            if progress:
                progress(min(start + len(batch), total), total, batch[-1])
            continue
        for offset, symbol in enumerate(batch, start=1):
            try:
                frame = _to_frame(downloaded, symbol)
                # Yahoo may include a partial current-session bar; retain only
                # dates strictly before the current US calendar date (pre-market scan).
                today_us = pd.Timestamp.now(tz="America/New_York").date()
                frame = frame.loc[[idx.date() < today_us for idx in frame.index]]
                if len(frame) < 2:
                    data_insufficient.append({"ticker": symbol, "reason": "확정 정규장 일봉 데이터 없음 또는 부족"})
                    continue
                latest_scan_date = max(latest_scan_date or frame.index[-1].strftime("%Y-%m-%d"), frame.index[-1].strftime("%Y-%m-%d"))
                indicators = calculate_indicators(frame)
                signal = latest_signal(frame)
                weekly_frame = resample_weekly_ohlcv(frame)
                weekly_indicators = calculate_indicators(weekly_frame)
                weekly = _weekly_summary(weekly_indicators)
                # 260 sessions are required only to calculate MA240.
                # This is not a discovery gate; candidates with sufficient
                # daily and weekly indicators remain eligible with the -20 penalty.
                if not signal.get("ready") or not weekly.get("ready"):
                    data_insufficient.append({
                        "ticker": symbol,
                        "reason": signal.get("reason") or weekly.get("reason") or "필수 기술지표 데이터 부족",
                    })
                    continue
                last = indicators.iloc[-1]
                close = _number(last.get("종가"))
                volume = _number(last.get("거래량"))
                trading_value_usd = close * volume if close is not None and volume is not None else None
                avg20_usd = _number((indicators["종가"] * indicators["거래량"]).tail(20).mean())
                checks = signal.get("checks") or {}
                if checks.get("rsi_cross_and_rising"):
                    stages["rsi"] += 1
                    if checks.get("macd_cross_and_rising"):
                        stages["macd"] += 1
                        if checks.get("ma10_breakout"):
                            stages["ma10"] += 1
                            if trading_value_usd is not None and trading_value_usd * fx >= 500_000_000:
                                stages["trading_value"] += 1
                                if weekly.get("close") is not None and weekly.get("ma10") is not None and weekly["close"] > weekly["ma10"]:
                                    stages["weekly_ma10"] += 1
                checks_out = {
                    "rsi_cross_and_rising": bool(checks.get("rsi_cross_and_rising")),
                    "macd_cross_and_rising": bool(checks.get("macd_cross_and_rising")),
                    "ma10_breakout": bool(checks.get("ma10_breakout")),
                    "trading_value_min": trading_value_usd is not None and trading_value_usd * fx >= 500_000_000,
                    "weekly_close_above_ma10": weekly.get("close") is not None and weekly.get("ma10") is not None and weekly["close"] > weekly["ma10"],
                }
                avg20_liquidity_ok = avg20_usd is not None and avg20_usd * fx >= 2_000_000_000
                if not all(checks_out.values()) or not avg20_liquidity_ok or not weekly.get("ready"):
                    continue
                ma240 = _number(last.get("MA240"))
                weekly_score = int(weekly.get("grade_score") or 0)
                if ma240 is None:
                    penalty, status, reason = 20, "ma240_unavailable", "MA240 데이터 부족"
                elif close < ma240:
                    penalty, status, reason = 15, "ma240_below", "종가가 MA240 아래"
                else:
                    penalty, status, reason = 0, "normal", "종가가 MA240 이상"
                signal["timing"] = signal.get("timing")
                matches.append({
                    "ticker": symbol, "name": names.get(symbol, symbol),
                    "trading_date": indicators.index[-1].strftime("%Y-%m-%d"),
                    "signal": signal, "discovery": {"ready": True, "matched": True, "checks": checks_out},
                    "matched": True, "weekly": weekly,
                    "scan_score": max(0, weekly_score - penalty),
                    "scan_score_penalty": penalty, "scan_status": status,
                    "scan_status_reason": reason,
                    "latest": {
                        "close": close, "change_pct": (
                            (close / _number(indicators.iloc[-2].get("종가")) - 1) * 100
                            if len(indicators) > 1 and _number(indicators.iloc[-2].get("종가")) else None
                        ),
                        "volume": volume, "trading_value": trading_value_usd * fx if trading_value_usd is not None else None,
                        "trading_value_usd": trading_value_usd,
                        "avg20_trading_value": avg20_usd * fx if avg20_usd is not None else None,
                        "ma10": _number(last.get("MA10")), "ma240": ma240,
                        "rsi10": _number(last.get("RSI10")), "rsi14": _number(last.get("RSI14")),
                        "volume_ratio": volume / _number(last.get("VOLUME_MA10")) if _number(last.get("VOLUME_MA10")) else None,
                        "atr14": _number(last.get("ATR14")), "support20": _number(last.get("LOW20")),
                        "resistance20": _number(last.get("HIGH20")),
                        "trade_plan": _trade_plan(close, _number(last.get("ATR14"))),
                    },
                })
            except Exception as exc:
                errors.append({"ticker": symbol, "error": str(exc)[:180]})
            if progress:
                progress(min(start + offset, total), total, symbol)
    grade_order = {"A": 0, "B": 1, "C": 2}
    matches.sort(key=lambda item: (
        grade_order.get((item.get("weekly") or {}).get("grade", "C"), 2),
        -(item.get("scan_score") or 0),
        -((item.get("latest") or {}).get("volume_ratio") or 0),
    ))
    grade_counts = {grade: sum(1 for item in matches if (item.get("weekly") or {}).get("grade") == grade) for grade in ("A", "B", "C")}
    return {
        "market": "US", "date": latest_scan_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "scanned": total, "stage_counts": stages, "matches": matches,
        "grade_counts": grade_counts, "error_count": len(errors), "errors": errors[:30],
        "data_insufficient_count": len(data_insufficient),
        "data_insufficient": data_insufficient[:30],
        "exchange_scope": ["NASDAQ", "NYSE"], "currency": "USD",
        "usdkrw": round(fx, 2), "daily_trading_value_min_krw": 500_000_000,
        "avg20_trading_value_min_krw": 2_000_000_000,
    }


def analyze_us_ticker(ticker: str) -> dict:
    """Return a chart-compatible technical analysis payload for one US ticker."""
    import yfinance as yf
    from .analyzer import _number, _trade_plan, _weekly_summary
    symbol = ticker.replace(".", "-").upper()
    history = yf.Ticker(symbol).history(period="2y", interval="1d", auto_adjust=True)
    frame = _to_frame(history, symbol)
    today_us = pd.Timestamp.now(tz="America/New_York").date()
    frame = frame.loc[[idx.date() < today_us for idx in frame.index]]
    if len(frame) < 2:
        raise ValueError("미국장 확정 일봉 데이터가 부족합니다.")
    indicators = calculate_indicators(frame)
    weekly_indicators = calculate_indicators(resample_weekly_ohlcv(frame))
    signal = latest_signal(frame)
    weekly = _weekly_summary(weekly_indicators)
    last = indicators.iloc[-1]
    previous = indicators.iloc[-2]
    close = _number(last.get("종가"))
    volume = _number(last.get("거래량"))
    fx = _usdkrw_rate()
    trading_value_usd = close * volume if close is not None and volume is not None else None
    change_pct = (close / _number(previous.get("종가")) - 1) * 100 if close and _number(previous.get("종가")) else None

    def records(data):
        output = []
        for index, row in data.tail(130).iterrows():
            item = {"date": index.strftime("%Y-%m-%d")}
            for key in ("시가", "고가", "저가", "종가", "거래량", "MA10", "MA20", "MA60", "MA240", "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "MACD", "MACD_SIGNAL", "MACD_HIST", "RSI10", "RSI14"):
                value = _number(row.get(key))
                item[key] = value
            output.append(item)
        return output

    checks = signal.get("checks") or {}
    trading_ok = trading_value_usd is not None and trading_value_usd * fx >= 500_000_000
    weekly_ok = weekly.get("close") is not None and weekly.get("ma10") is not None and weekly["close"] > weekly["ma10"]
    discovery_checks = {
        "rsi_cross_and_rising": bool(checks.get("rsi_cross_and_rising")),
        "macd_cross_and_rising": bool(checks.get("macd_cross_and_rising")),
        "ma10_breakout": bool(checks.get("ma10_breakout")),
        "trading_value_min": trading_ok,
        "weekly_close_above_ma10": weekly_ok,
    }
    matched = all(discovery_checks.values()) and weekly.get("ready") is True
    if not matched:
        weekly = dict(weekly)
        weekly["grade"] = None
        weekly["grade_score"] = None
        weekly["grade_reason"] = "발굴 조건 미충족으로 A/B/C 등급 미부여 · " + (weekly.get("grade_reason") or "")
    try:
        name = yf.Ticker(symbol).get_info().get("shortName") or symbol
    except Exception:
        name = symbol
    return {
        "ticker": symbol, "name": name, "trading_date": indicators.index[-1].strftime("%Y-%m-%d"),
        "currency": "USD", "exchange_scope": ["NASDAQ", "NYSE"], "usdkrw": round(fx, 2),
        "signal": signal, "discovery": {"ready": True, "checks": discovery_checks, "matched": matched},
        "matched": matched, "weekly": weekly, "weekly_ohlcv": records(weekly_indicators.tail(52)),
        "latest": {
            "close": close, "change_pct": change_pct, "volume": volume,
            "trading_value": trading_value_usd * fx if trading_value_usd is not None else None,
            "trading_value_usd": trading_value_usd, "ma10": _number(last.get("MA10")),
            "ma20": _number(last.get("MA20")), "ma60": _number(last.get("MA60")),
            "ma240": _number(last.get("MA240")), "rsi10": _number(last.get("RSI10")),
            "rsi14": _number(last.get("RSI14")), "macd": _number(last.get("MACD")),
            "macd_signal": _number(last.get("MACD_SIGNAL")), "macd_hist": _number(last.get("MACD_HIST")),
            "volume_ratio": volume / _number(last.get("VOLUME_MA10")) if volume and _number(last.get("VOLUME_MA10")) else None,
            "atr14": _number(last.get("ATR14")), "support20": _number(last.get("LOW20")),
            "resistance20": _number(last.get("HIGH20")), "trade_plan": _trade_plan(close, _number(last.get("ATR14"))),
        },
        "ohlcv": records(indicators),
    }
