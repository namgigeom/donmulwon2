"""Read-only Toss Securities Open API client."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://openapi.tossinvest.com"


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries from the repository .env without overriding OS env."""
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


class TossApiError(RuntimeError):
    pass


class TossClient:
    """OAuth client and read-only market/account data access. No order methods exist."""

    def __init__(self):
        _load_local_env()
        self.client_id = os.getenv("TOSS_CLIENT_ID") or os.getenv("TOSS_API_KEY", "")
        self.client_secret = os.getenv("TOSS_CLIENT_SECRET") or os.getenv("TOSS_API_SECRET", "")
        self.account_seq = os.getenv("TOSS_ACCOUNT_SEQ", "")
        self._token = ""
        self._token_expires_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _request_json(self, method: str, path: str, *, params=None, data=None, token_required=True):
        url = BASE_URL + path
        if params:
            url += "?" + urlencode(params)
        headers = {"Accept": "application/json"}
        body = None
        if data is not None:
            body = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if token_required:
            headers["Authorization"] = f"Bearer {self.access_token()}"
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise TossApiError(f"Toss API HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise TossApiError(f"Toss API 연결/응답 오류: {exc}") from exc

    def access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        if not self.configured:
            raise TossApiError(
                "Toss API 인증정보가 없습니다. .env에 TOSS_CLIENT_ID와 "
                "TOSS_CLIENT_SECRET을 입력하세요. (기존 TOSS_API_KEY/SECRET도 지원)"
            )
        payload = self._request_json(
            "POST", "/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            token_required=False,
        )
        token = payload.get("access_token")
        if not token:
            raise TossApiError(f"토큰 발급 응답에 access_token이 없습니다: {payload}")
        self._token = token
        self._token_expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    @staticmethod
    def _result(payload):
        return payload.get("result", payload) if isinstance(payload, dict) else payload

    def candles(self, symbol: str, count: int = 420):
        """Fetch unique daily candles; Toss before/nextBefore pagination is inclusive."""
        rows = []
        seen_timestamps = set()
        before = None

        while len(rows) < count:
            # The next page includes its boundary candle, so request one extra
            # item to still reach the requested number of unique trading days.
            remaining = count - len(rows)
            page_count = min(200, remaining + (1 if before else 0))
            params = {
                "symbol": symbol,
                "interval": "1d",
                "count": page_count,
                "adjusted": "true",
            }
            if before:
                params["before"] = before

            payload = self._result(self._request_json("GET", "/api/v1/candles", params=params))
            if isinstance(payload, list):
                page, next_before = payload, None
            elif isinstance(payload, dict):
                page = payload.get("candles") or payload.get("items") or payload.get("data") or []
                next_before = payload.get("nextBefore") or payload.get("next_before")
            else:
                page, next_before = [], None

            if not page:
                break

            for candle in page:
                timestamp = candle.get("timestamp") if isinstance(candle, dict) else None
                # Toss documents timestamp as a required field for every candle.
                # Keep the newest occurrence when an inclusive page boundary repeats.
                if timestamp is None or timestamp in seen_timestamps:
                    continue
                seen_timestamps.add(timestamp)
                rows.append(candle)
                if len(rows) >= count:
                    break

            if not next_before or next_before == before:
                break
            before = next_before

        return rows[:count]

    def stock_info(self, symbol: str):
        payload = self._request_json("GET", "/api/v1/stocks", params={"symbols": symbol})
        result = self._result(payload)
        if isinstance(result, list):
            return result[0] if result else {}
        if isinstance(result, dict):
            items = result.get("stocks") or result.get("items")
            return items[0] if isinstance(items, list) and items else result
        return {}

    def accounts(self):
        return self._result(self._request_json("GET", "/api/v1/accounts"))

    def holdings(self):
        if not self.account_seq:
            raise TossApiError("계좌 조회에는 .env의 TOSS_ACCOUNT_SEQ가 필요합니다.")
        url = BASE_URL + "/api/v1/holdings"
        request = Request(url, headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token()}",
            "X-Tossinvest-Account": self.account_seq,
        })
        try:
            with urlopen(request, timeout=20) as response:
                return self._result(json.loads(response.read().decode("utf-8")))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise TossApiError(f"Toss API HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise TossApiError(f"Toss API 연결/응답 오류: {exc}") from exc
