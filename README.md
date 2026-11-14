# DONMULWON 2

국내 주식시장(KOSPI/KOSDAQ)에서 사용자가 정의한 기술적 조건을 충족하는 종목을 발굴하고, 차트·추세·위험·진입 기준을 확인하는 개인용 투자 분석 사이트입니다. 자동매매/주문 기능은 없습니다.

## 웹 버전 실행 (Windows 10/11)

Node.js LTS가 설치되어 있는지 확인한 뒤 저장소 루트에서 아래 명령어를 실행합니다.

```powershell
git pull origin web-rebuild
powershell -ExecutionPolicy Bypass -File .\start_donmulwon.ps1
```

런처가 프로젝트 전용 Python 가상환경과 필요한 의존성을 확인하고, 백엔드와 프론트엔드를 별도 터미널에서 실행한 뒤 브라우저를 엽니다. 서버를 사용하는 동안 두 터미널 창을 닫지 마세요.

수동 실행이 필요한 경우 터미널 두 개를 사용합니다.

**터미널 1 — Python API**
```powershell
cd C:\vscode\donmulwon2_starter
.\.venv\Scripts\Activate.ps1
python -m uvicorn donmulwon2.api:app --reload --host 127.0.0.1 --port 8000
```

**터미널 2 — 웹사이트**
```powershell
cd C:\vscode\donmulwon2_starter\web
npm install
npm run dev -- --host 127.0.0.1
```

- 웹사이트: http://localhost:5173
- API 상태: http://127.0.0.1:8000/api/health
- API 문서: http://127.0.0.1:8000/docs


## KRX 데이터 연결 설정

현재 pykrx의 인증이 필요한 KRX 조회 기능을 사용하려면 KRX 회원 계정 인증정보가 필요할 수 있습니다. 저장소 루트의 `.env.example`을 `.env`로 복사한 뒤 아래 항목을 입력하세요.

```dotenv
KRX_ID=본인_KRX_로그인_ID
KRX_PW=본인_KRX_로그인_비밀번호
```

- KRX 정보데이터시스템 회원 계정 정보를 사용합니다.
- 비밀번호를 채팅이나 GitHub에 올리지 마세요. `.env`는 Git 제외 대상입니다.
- 입력 후 백엔드 서버를 완전히 재시작하세요.
- 인증정보를 설정해도 KRX 서버 장애나 접속 제한 중에는 데이터 조회가 실패할 수 있습니다.
- KRX 계정 등록/로그인 및 데이터 이용 조건은 KRX 공식 사이트에서 확인하세요.

## 핵심 발굴 기준

일봉 기준 아래 세 조건을 모두 충족해야 스캔 후보가 됩니다.

1. RSI(10)가 RSI(14)를 상향 돌파하고, 두 RSI가 모두 전일 대비 상승
2. MACD(5,10,9)가 시그널선을 상향 돌파하고 MACD가 상승
3. 종가가 MA10을 전일 종가 기준 아래에서 당일 종가 기준 위로 상향 돌파

주봉은 큰 추세와 위험을 파악하는 참고 정보이며 일봉 필수 조건을 대체하지 않습니다. 240일선 아래에 있다는 이유만으로 후보를 자동 제외하지 않고 위험 표시로 남깁니다.

## 현재 구현된 웹 기능

- KOSPI/KOSDAQ 시장 게시판: 상승·하락 종목 수, 거래대금, 기준 거래일
- 종목코드 검색 및 일봉/완료 주봉 차트
- 캔들, MA10/20/60, 볼린저밴드, 거래량, MACD, RSI 시각화
- KOSPI/KOSDAQ 전체 종목 조건 스캔
- 백그라운드 스캔 작업 및 진행률/현재 종목 표시
- 후보별 RSI/MACD/MA10 조건, 주봉 추세, 240일선 위험 표시
- ATR(14) 기반 진입 참고 구간, 손절, 2R/3R 목표 가격
- 단일 종목 분석 시 필수 신호 충족 여부와 참고 가격 표시
- SQLite 분석 기록 저장 및 최근 기록 조회 API
- 토스증권 Open API 읽기 전용 인증, 계좌/보유종목 조회, 개별 종목 일봉 데이터 연결
- 토스 계좌 잔고는 핵심 종목 발굴 화면에 표시하지 않음

## 데이터 소스 및 한계

- KOSPI/KOSDAQ 전 종목 목록과 시장 전체 스캔은 KRX/pykrx 데이터에 기반합니다. 종목 수가 많아 스캔 완료까지 시간이 걸릴 수 있습니다.
- 개별 종목 상세 일봉은 토스 API 인증정보가 있으면 토스를 우선 사용합니다. 전체 시장을 토스 API로 수천 번 호출하지 않습니다.
- 주봉은 일봉 OHLCV에서 완료된 주만 집계합니다.
- ATR 가격은 변동성에 따른 기계적 참고값입니다. 갭, 거래량, 유동성, 수수료, 시장 급변을 모두 반영한 보장 가격이 아닙니다.
- 현재는 종가 확정 일봉 중심이며 실시간 호가·체결 감시 기능은 없습니다.
- 업종/테마별 강도, 뉴스 기반 AI 토론·검증, 전략 백테스트는 추가 개발 대상입니다.
- API 개발 서버는 localhost 전용으로 실행하세요. 인증 없는 API를 공용 인터넷에 노출하지 마세요.

## 친구에게 링크로 공유 (최대 2명 사용 권장)

공유 기능은 기존 개인용 서버와 분리된 별도 인스턴스로 실행합니다.

- 개인용 웹사이트/API: 기존 `start_donmulwon.ps1` (5173 / 8000)
- 공유용 웹사이트/API: `start_donmulwon_share.ps1` (5174 / 8001)
- 공유용 API는 `DONMULWON_SHARE_MODE=1`로 실행되며 `/api/toss` 및 하위 경로를 서버에서 HTTP 404로 차단합니다.
- 공유용 웹사이트는 상대 경로 `/api`를 사용하고 Vite 프록시가 공유 API(8001)로 전달합니다.
- 공유용 분석 기록은 개인용 `data/donmulwon2.db`와 분리된 `data/donmulwon2_share.db`를 사용합니다.
- Cloudflare Quick Tunnel이 공개 `trycloudflare.com` 링크를 만듭니다. 친구는 별도 프로그램이나 계정 없이 링크를 브라우저에 입력하면 됩니다.
- **링크 자체에 로그인/이메일 인증은 없습니다. 링크를 가진 누구나 접속할 수 있으므로 친구에게만 비공개로 전달하세요.**
- 링크는 터널을 재시작할 때마다 바뀝니다. 이 PC와 공유 서버, cloudflared가 실행 중일 때만 접속할 수 있습니다.
- Quick Tunnel은 테스트/임시 공유용이며 가동시간 보장이나 고정 주소를 제공하지 않습니다. 최대 200개 동시 진행 요청 제한과 SSE 미지원 제한이 있습니다.

Windows 공유 실행:
```powershell
git pull origin web-rebuild
powershell -ExecutionPolicy Bypass -File .\start_donmulwon_share.ps1
```

스크립트가 필요하면 winget으로 `cloudflared`를 설치하고, 공유용 API(8001)와 웹사이트(5174)를 실행한 뒤 Cloudflare 터널을 시작합니다. 터미널에 출력되는 `https://....trycloudflare.com` 주소를 친구에게 전달하세요. 터널을 중지하려면 실행 중인 PowerShell 창에서 Ctrl+C를 누르세요.

공유용 API의 `/api/toss/status`, `/api/toss/accounts`, `/api/toss/holdings`는 404로 차단됩니다. 공유용 분석 기록은 두 사용자가 함께 보며, 기존 개인 분석 기록은 공유하지 않습니다. 공개 링크를 아는 사람이면 누구나 분석 기능을 사용할 수 있으므로 링크를 공개 게시판 등에 올리지 마세요.

## 기존 데스크톱 앱

기존 Python/PySide6 데스크톱 프로그램은 레거시로 보존합니다. 웹 버전이 충분히 검증되기 전까지 삭제하거나 대체하지 않습니다.
