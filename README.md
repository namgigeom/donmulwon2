# DONMULWON 2

한국 주식시장 일봉 데이터를 기반으로 종목을 탐색하고 기술적 지표를 분석하는 데스크톱 프로그램입니다. 자동매매 기능은 없습니다.

## 웹사이트 개발 (진행 중)

React + TypeScript + Vite 기반 웹 프론트엔드는 `web/`에서 개발합니다. 기존 Python/PySide6 분석 앱은 보존하며, 웹 버전이 기능 검증을 통과하기 전까지 삭제하지 않습니다.

### 웹 프론트엔드 및 API 실행

터미널 1에서 Python API를 실행합니다.

```powershell
# 저장소 루트에서
pip install -r requirements.txt
uvicorn donmulwon2.api:app --reload --host 127.0.0.1 --port 8000
```

터미널 2에서 React 웹사이트를 실행합니다.

```powershell
cd web
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`을 엽니다. API 상태 확인은 `http://127.0.0.1:8000/api/health`, API 문서는 `http://127.0.0.1:8000/docs`입니다.

현재 API는 기존 Python 분석 엔진을 웹에서 호출할 수 있도록 연결하는 초기 단계입니다. KRX 시장 게시판, 개별 종목 분석, KOSPI/KOSDAQ 스캔 엔드포인트를 제공합니다. OpenRouter와 토스증권 API는 아직 연결되지 않았으며, 연결 전에는 실제 데이터처럼 보이는 임의 숫자를 표시하지 않습니다.

## 실행 환경
- Windows 10/11
- Python 3.11 이상

## 설치 및 실행 (PowerShell)
```powershell
git pull origin main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m donmulwon2.app
```

## 구현된 기능
- 승인된 픽셀아트 배경 위에 실제 Qt 위젯을 얹는 대시보드
- 시작 후 KRX 시장 게시판 자동 갱신
- KOSPI/KOSDAQ 지수 종가·등락률, 상승/하락 종목 수, 전체 거래대금
- KOSPI/KOSDAQ 투자자별 순매수 데이터
- 종목코드 검색 후 실제 일봉 분석
- 캔들 차트, MA10/20/60, RSI(10/14), MACD(5/10/9) 히스토그램 및 MACD/Signal 선
- ATR(14), 20일 지지/저항 참고선, 52주 고점 대비 하락률
- 종목 발굴: RSI10이 RSI14를 상향 교차하고 두 RSI가 상승, MACD(5/10/9) 상향 교차 및 상승, 종가의 MA10 상향 돌파가 모두 발생한 종목
- KOSPI 또는 KOSDAQ 전체 종목 검색 및 진행률 표시
- SQLite에 종목 분석과 시장 게시판 데이터 기록 및 GUI 분석 이력 탭 제공
- 네트워크/원천 데이터 오류를 표시하며 임의 시세나 가짜 분석값을 생성하지 않음

## 아직 연결하지 않은 기능
- 테마/업종별 강도와 뉴스 수집
- 뉴스 근거를 포함한 AI 시장 요약
- 매물대, ATR 기반 변동성, 지지/저항 분석
- 진입/손절/목표가 산출 규칙과 수수료·슬리피지를 포함한 백테스트
- 저장된 분석 이력의 GUI 조회 화면
- 기술적 지지/저항 및 ATR 지표는 참고 정보이며, 검증된 매수·매도 가격을 뜻하지 않음
- 실시간 호가/체결 데이터 (현재 KRX 일봉 데이터 중심)

## 데이터 해석 주의
- KRX 원천 데이터가 정상 수신된 마지막 거래일을 기준으로 표시합니다.
- KRX 일봉은 실시간 체결/호가가 아닙니다.
- 시장 한줄 요약은 현재 상승·하락 폭과 거래대금을 요약한 규칙 기반 문구이며, 뉴스/테마 AI 분석이 아닙니다.
- 검색은 종목별 과거 일봉을 순차 조회하므로 전체 시장 검색에 시간이 오래 걸릴 수 있습니다.
- 데이터 수신 실패는 미수신으로 표시하고 추정 숫자로 대체하지 않습니다.
