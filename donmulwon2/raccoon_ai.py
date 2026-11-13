"""OpenRouter-backed daily market interpretation for the DONMULWON raccoon analyst."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_market_facts(bulletins: list[dict]) -> dict:
    """Select only fields actually supplied by KRX market bulletins."""
    markets = []
    for bulletin in bulletins:
        sectors = bulletin.get("sectors") or []
        valid_sectors = [
            item for item in sectors
            if isinstance(item, dict) and isinstance(item.get("change_pct"), (int, float))
        ]
        ordered = sorted(valid_sectors, key=lambda item: item["change_pct"])
        flows = (bulletin.get("investor_flows") or {}).get("values") or {}
        markets.append({
            "market": bulletin.get("market"),
            "date": bulletin.get("date"),
            "index": bulletin.get("index"),
            "advancers": bulletin.get("advancers"),
            "decliners": bulletin.get("decliners"),
            "unchanged": bulletin.get("unchanged"),
            "ticker_count": bulletin.get("ticker_count"),
            "trading_value_krw": bulletin.get("trading_value"),
            "strongest_sectors": ordered[-5:][::-1],
            "weakest_sectors": ordered[:5],
            "investor_flows": flows,
            "sector_data_status": bulletin.get("sector_status"),
            "investor_flow_status": bulletin.get("flow_status"),
        })
    return {"markets": markets}


def generate_market_note(market_facts: dict) -> tuple[str, str]:
    """Generate a fresh Korean market interpretation from the supplied facts."""
    _load_local_env()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY가 .env에 설정되지 않았습니다.")
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash").strip()
    prompt = (
        "너는 돈물원의 수석 시장 애널리스트 너구리다. 제공된 당일 KOSPI·KOSDAQ 데이터만 분석해 "
        "오늘 시장 상황과 투자 대응 조언을 작성해라. 지수 방향, 상승·하락 종목 수, 주도·부진 업종, "
        "투자자 수급 중 실제 확인된 근거를 우선 사용해라. null 또는 미수신 항목은 추측하지 마라. "
        "수치 나열보다 시장의 의미와 투자자가 오늘 취할 태도를 말해라. 한국어 한두 문장, 45~90자 정도로 "
        "작성하고 너구리 말투를 자연스럽게 섞어 마지막을 '너굴'로 끝내라. 매수·매도 단정이나 수익 보장은 "
        "금지한다. 출력은 조언 본문만 작성해라.\n시장 데이터: "
        + json.dumps(market_facts, ensure_ascii=False)
    )
    body = json.dumps({
        "model": model,
        "temperature": 0.65,
        "max_tokens": 180,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/namgigeom/donmulwon2",
            "X-Title": "DONMULWON 2",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=35) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OpenRouter 연결/응답 오류: {exc}") from exc
    choices = payload.get("choices") or []
    content = (choices[0].get("message") or {}).get("content") if choices else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter 응답에 생성된 조언이 없습니다.")
    note = " ".join(content.strip().replace('"', "").split())
    if not note.endswith("너굴"):
        note = note.rstrip(" .!。") + " 너굴"
    return note, model
