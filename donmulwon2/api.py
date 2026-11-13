"""FastAPI bridge exposing the existing DONMULWON analysis engine to the web UI."""
from __future__ import annotations

import re

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import DonmulwonAnalyzer

app = FastAPI(
    title="DONMULWON 2 API",
    version="0.1.0",
    description="Read-only web API for Korean stock screening and technical analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _market_name(market: str) -> str:
    normalized = market.upper()
    if normalized not in {"KOSPI", "KOSDAQ"}:
        raise HTTPException(status_code=404, detail="market must be KOSPI or KOSDAQ")
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


@app.post("/api/scan/{market}")
def scan_market(
    market: str,
    limit: int | None = Query(default=None, ge=1, le=3000),
):
    """Run the existing three-condition daily scanner for KOSPI or KOSDAQ."""
    selected = _market_name(market)
    analyzer = DonmulwonAnalyzer()
    result = analyzer.scan_market(selected, limit=limit)
    return _require_success(result)
