"""FastAPI bridge exposing the existing DONMULWON analysis engine to the web UI."""
from __future__ import annotations

import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import DonmulwonAnalyzer
from .toss_api import TossApiError, TossClient

app = FastAPI(
    title="DONMULWON 2 API",
    version="0.1.0",
    description="Read-only web API for Korean stock screening and technical analysis.",
)

_scan_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="donmulwon-scan")
_scan_jobs = {}
_scan_lock = threading.Lock()
_raccoon_note_lock = threading.Lock()


def _run_scan_job(job_id, market, limit):
    try:
        analyzer = DonmulwonAnalyzer()

        def update_progress(done, total, ticker):
            with _scan_lock:
                job = _scan_jobs.get(job_id)
                if job is not None:
                    job.update({"progress": done, "total": total, "current_ticker": ticker})

        result = analyzer.scan_market(market, progress=update_progress, limit=limit)
        with _scan_lock:
            job = _scan_jobs.get(job_id)
            if job is not None:
                if result.ok:
                    job.update({"status": "completed", "progress": job.get("total", 0),
                                "result": result.data, "finished_at": datetime.now().isoformat(timespec="seconds")})
                else:
                    job.update({"status": "failed", "error": result.message,
                                "finished_at": datetime.now().isoformat(timespec="seconds")})
    except Exception as exc:
        with _scan_lock:
            job = _scan_jobs.get(job_id)
            if job is not None:
                job.update({"status": "failed", "error": str(exc),
                            "finished_at": datetime.now().isoformat(timespec="seconds")})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _market_name(market: str) -> str:
    normalized = market.upper()
    if normalized not in {"KOSPI", "KOSDAQ", "ALL"}:
        raise HTTPException(status_code=404, detail="market must be ALL, KOSPI or KOSDAQ")
    return normalized


def _require_success(result):
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.message or "KRX data request failed")
    return result.data


@app.get("/api/health")
def health():
    return {"ok": True, "service": "donmulwon2-api", "analysis_engine": "python"}


@app.get("/api/market/{market}/bulletin")
def market_bulletin(market: str):
    """Return the latest KRX breadth, trading value and investor-flow bulletin."""
    selected = _market_name(market)
    analyzer = DonmulwonAnalyzer()
    return _require_success(analyzer.market_bulletin(selected))


@app.get("/api/stocks/{ticker}")
def analyze_stock(ticker: str):
    """Analyze one Korean stock by its six-digit ticker."""
    if not re.fullmatch(r"\d{6}", ticker):
        raise HTTPException(status_code=422, detail="ticker must contain exactly six digits")
    analyzer = DonmulwonAnalyzer()
    return _require_success(analyzer.analyze_ticker(ticker))


@app.get("/api/stocks/{ticker}/rsi-debug")
def debug_stock_rsi(ticker: str):
    """Expose candle provenance and recent RSI inputs for troubleshooting."""
    if not re.fullmatch(r"\d{6}", ticker):
        raise HTTPException(status_code=422, detail="ticker must contain exactly six digits")

    analyzer = DonmulwonAnalyzer()
    history = analyzer.provider.ticker_history(ticker, days=420, use_toss=True)
    frame = _require_success(history)
    from .indicators import calculate_indicators

    indicators = calculate_indicators(frame)
    if indicators.empty:
        raise HTTPException(status_code=502, detail="RSI 계산용 캔들 데이터가 비어 있습니다.")

    import pandas as pd

    close = pd.to_numeric(frame["종가"], errors="coerce")
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    def latest_rsi(avg_gain, avg_loss):
        gain_value, loss_value = avg_gain.iloc[-1], avg_loss.iloc[-1]
        if pd.isna(gain_value) or pd.isna(loss_value):
            return None
        if loss_value == 0:
            return 50.0 if gain_value == 0 else 100.0
        return round(float(100 - 100 / (1 + gain_value / loss_value)), 2)

    formula_comparison = {}
    for period in (10, 14):
        formula_comparison[str(period)] = {
            "wilder_sma_seed": round(float(indicators.iloc[-1][f"RSI{period}"]), 2),
            "ewm_wilder_adjust_false": latest_rsi(
                gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean(),
                losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean(),
            ),
            "ewm_wilder_adjust_true": latest_rsi(
                gains.ewm(alpha=1 / period, min_periods=period, adjust=True).mean(),
                losses.ewm(alpha=1 / period, min_periods=period, adjust=True).mean(),
            ),
            "simple_rolling_cutler": latest_rsi(
                gains.rolling(period, min_periods=period).mean(),
                losses.rolling(period, min_periods=period).mean(),
            ),
            "ema_standard": latest_rsi(
                gains.ewm(span=period, min_periods=period, adjust=False).mean(),
                losses.ewm(span=period, min_periods=period, adjust=False).mean(),
            ),
        }

    recent = indicators.tail(30)
    latest = indicators.iloc[-1]
    return {
        "ticker": ticker,
        "source": history.message,
        "adjusted_prices": True if history.message.startswith("Toss") else None,
        "bar_count": int(len(frame)),
        "first_date": frame.index[0].strftime("%Y-%m-%d"),
        "last_date": frame.index[-1].strftime("%Y-%m-%d"),
        "latest_close": float(latest["종가"]),
        "rsi10": float(latest["RSI10"]) if latest.get("RSI10") == latest.get("RSI10") else None,
        "rsi14": float(latest["RSI14"]) if latest.get("RSI14") == latest.get("RSI14") else None,
        "formula_comparison": formula_comparison,
        "recent_bars": [
            {
                "date": index.strftime("%Y-%m-%d"),
                "close": float(row["종가"]),
                "rsi10": float(row["RSI10"]) if row.get("RSI10") == row.get("RSI10") else None,
                "rsi14": float(row["RSI14"]) if row.get("RSI14") == row.get("RSI14") else None,
            }
            for index, row in recent.iterrows()
        ],
    }


@app.post("/api/scan/{market}")
def scan_market(
    market: str,
    limit: int | None = Query(default=None, ge=1),
):
    """Start a background scan and return a job ID immediately."""
    selected = _market_name(market)
    with _scan_lock:
        active = next((job for job in _scan_jobs.values()
                       if job["market"] == selected and job["status"] == "running"), None)
        if active:
            return {"job_id": active["job_id"], "status": "running", "reused": True}
        job_id = uuid.uuid4().hex
        _scan_jobs[job_id] = {
            "job_id": job_id, "market": selected, "status": "running",
            "progress": 0, "total": 0, "current_ticker": None,
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
    _scan_executor.submit(_run_scan_job, job_id, selected, limit)
    return {"job_id": job_id, "status": "running", "reused": False}


@app.get("/api/scan/jobs/{job_id}")
def scan_job_status(job_id: str):
    """Return background scan progress or its completed result."""
    with _scan_lock:
        job = _scan_jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="스캔 작업을 찾을 수 없습니다.")
        return dict(job)


@app.get("/api/history")
def analysis_history(limit: int = Query(default=100, ge=1, le=200)):
    """Return five-day analysis history with current-price performance."""
    from .storage import AnalysisStore

    items = AnalysisStore().recent_analyses(limit)
    analyzer = DonmulwonAnalyzer()
    current_prices = {}
    for item in items:
        ticker = item["ticker"]
        if ticker not in current_prices:
            result = analyzer.analyze_ticker(
                ticker, save=False, include_ohlcv=False
            )
            current_prices[ticker] = (
                result.data.get("latest", {}).get("close")
                if result.ok else None
            )
        current = current_prices[ticker]
        baseline = item.get("baseline_price")
        item["current_price"] = current
        item["change_pct"] = (
            round((current / baseline - 1) * 100, 2)
            if isinstance(current, (int, float))
            and isinstance(baseline, (int, float)) and baseline > 0
            else None
        )
    return {"items": items, "retention_days": 5}



@app.get("/api/market/raccoon-note")
def raccoon_market_note():
    """Generate and cache one AI market interpretation per KRX trading date."""
    from .raccoon_ai import build_market_facts, generate_market_note
    from .storage import AnalysisStore

    with _raccoon_note_lock:
        store = AnalysisStore()
        analyzer = DonmulwonAnalyzer(store=store)
        bulletins = []
        for market in ("KOSPI", "KOSDAQ"):
            bulletin = store.latest_bulletin(market)
            if not bulletin:
                result = analyzer.market_bulletin(market)
                if not result.ok:
                    raise HTTPException(
                        status_code=502,
                        detail=f"{market} 시장 데이터 조회 실패: {result.message}",
                    )
                bulletin = result.data
            bulletin = dict(bulletin)
            bulletin["market"] = market
            bulletins.append(bulletin)

        dates = [item.get("date") for item in bulletins if item.get("date")]
        if not dates:
            raise HTTPException(status_code=503, detail="당일 시장 기준일을 확인할 수 없습니다.")
        trading_date = max(dates)
        cached = store.get_raccoon_note(trading_date)
        if cached:
            return {"status": "ready", **cached, "cached": True}

        facts = build_market_facts(bulletins)
        try:
            note, model = generate_market_note(facts)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        store.save_raccoon_note(trading_date, note, model, facts)
        return {
            "status": "ready",
            "trading_date": trading_date,
            "note": note,
            "model": model,
            "cached": False,
        }


@app.get("/api/toss/status")
def toss_status():
    client = TossClient()
    return {
        "configured": client.configured,
        "account_configured": bool(client.account_seq),
        "provider": "toss" if client.configured else "pykrx",
        "message": "Toss 인증정보 확인됨" if client.configured else "Toss 인증정보 미설정: 기존 pykrx 데이터 사용",
    }


@app.get("/api/toss/accounts")
def toss_accounts():
    client = TossClient()
    if not client.configured:
        raise HTTPException(status_code=503, detail="Toss API 인증정보가 설정되지 않았습니다.")
    try:
        return {"accounts": client.accounts()}
    except TossApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/toss/holdings")
def toss_holdings():
    client = TossClient()
    if not client.configured:
        raise HTTPException(status_code=503, detail="Toss API 인증정보가 설정되지 않았습니다.")
    try:
        return {"holdings": client.holdings()}
    except TossApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
