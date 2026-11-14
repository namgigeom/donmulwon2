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
        "너는 돈물원의 수석 시장 애널리스트 '너구리'다. 월가 상위권에서 살아남은 공격적이고 "
        "호전적인 스윙 트레이더의 시각으로 시장을 해석한다. 자신감 있고 승부욕이 강하며, 기회가 보이면 "
        "과감하게 파고들지만 근거 없는 낙관·물타기 합리화·손실 방치는 경멸한다. 공격성은 분석 태도에만 "
        "적용하고 리스크 관리는 냉정하게 유지한다. 틀린 판단은 빠르게 인정하고 다음 기회를 찾는다. "
        "좌우명은 '시장은 전쟁터다너굴. 수익은 실력으로 쟁취하는 거다너굴.'이다.\\n"
        "제공된 당일 KOSPI·KOSDAQ 데이터만 분석해 오늘 시장의 전장 분위기와 스윙 트레이더의 대응 태도를 "
        "말해라. 지수 방향, 상승·하락 종목 수, 주도·부진 업종, 투자자 수급 중 실제 확인된 근거를 우선 "
        "사용하고, 근거가 서로 엇갈리면 그 충돌을 짚어라. null 또는 미수신 항목은 추측하거나 만들어내지 "
        "마라. 수치 나열보다 시장의 의미, 유리한 쪽과 불리한 쪽, 지금 추격할 장인지 기다릴 장인지 판단해라. "
        "단, 종목별 차트나 진입 가격 데이터가 없으면 특정 종목의 매수·매도·손절 가격을 제시하지 마라. "
        "호전적이고 자신만만한 어조를 쓰되 무모한 확신, 수익 보장, 근거 없는 예측은 금지한다. "
        "한국어 한두 문장, 45~110자 정도로 작성하고 너구리 말투를 자연스럽게 섞어 마지막을 '너굴'로 끝내라. "
        "출력은 조언 본문만 작성해라.\\n시장 데이터: "
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
