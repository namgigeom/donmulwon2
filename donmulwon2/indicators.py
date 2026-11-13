"""Technical indicators used by DONMULWON 2. All calculations use daily OHLCV data."""
from __future__ import annotations

import pandas as pd


def calculate_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with RSI(10/14), MACD(5/10/9), MA10/20/60/120/240 and Bollinger bands."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    df = frame.copy().sort_index()
    close = pd.to_numeric(df["종가"], errors="coerce")
    delta = close.diff()

    def rsi(period: int) -> pd.Series:
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss.where(avg_loss.ne(0))
        result = 100 - (100 / (1 + rs))
        return result.where(avg_loss.ne(0), 100)

    df["RSI10"] = rsi(10)
    df["RSI14"] = rsi(14)
    ema_fast = close.ewm(span=5, adjust=False).mean()
    ema_slow = close.ewm(span=10, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]

    for period in (10, 20, 60, 120, 240):
        df[f"MA{period}"] = close.rolling(period, min_periods=period).mean()

    mid = close.rolling(20, min_periods=20).mean()
    std = close.rolling(20, min_periods=20).std(ddof=0)
    df["BB_UPPER"] = mid + 2 * std
    df["BB_MIDDLE"] = mid
    df["BB_LOWER"] = mid - 2 * std

    volume = pd.to_numeric(df.get("거래량", 0), errors="coerce")
    df["VOLUME_MA20"] = volume.rolling(20, min_periods=1).mean()
    return df


def latest_signal(frame: pd.DataFrame) -> dict:
    """Evaluate the user's three mandatory entry conditions on the latest completed bar."""
    if frame is None or len(frame) < 2:
        return {"ready": False, "reason": "지표 계산에 필요한 데이터가 부족합니다."}

    df = calculate_indicators(frame)
    prev, cur = df.iloc[-2], df.iloc[-1]
    required = ["RSI10", "RSI14", "MACD", "MACD_SIGNAL", "MA10"]
    if any(pd.isna(cur.get(key)) or pd.isna(prev.get(key)) for key in required):
        return {"ready": False, "reason": "지표 계산 기간이 충분하지 않습니다."}

    rsi_cross = prev["RSI10"] <= prev["RSI14"] and cur["RSI10"] > cur["RSI14"]
    rsi_rising = cur["RSI10"] > prev["RSI10"] and cur["RSI14"] > prev["RSI14"]
    macd_cross = prev["MACD"] <= prev["MACD_SIGNAL"] and cur["MACD"] > cur["MACD_SIGNAL"]
    macd_rising = cur["MACD"] > prev["MACD"] and cur["MACD_SIGNAL"] >= prev["MACD_SIGNAL"]
    ma_breakout = prev["종가"] <= prev["MA10"] and cur["종가"] > cur["MA10"]

    checks = {
        "rsi_cross_and_rising": bool(rsi_cross and rsi_rising),
        "macd_cross_and_rising": bool(macd_cross and macd_rising),
        "ma10_breakout": bool(ma_breakout),
    }
    return {
        "ready": True,
        "checks": checks,
        "matched": all(checks.values()),
        "rsi10": float(cur["RSI10"]),
        "rsi14": float(cur["RSI14"]),
        "macd": float(cur["MACD"]),
        "macd_signal": float(cur["MACD_SIGNAL"]),
        "close": int(cur["종가"]),
        "ma10": float(cur["MA10"]),
        "volume_ratio": float(cur["거래량"] / cur["VOLUME_MA20"]) if cur["VOLUME_MA20"] else None,
    }
