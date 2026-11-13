# DONMULWON 2 — Starter GUI

돈물원 2의 첫 번째 GUI 시제품입니다.

## 실행 환경
- Windows 10/11
- Python 3.11 이상 권장

## 실행 방법 (PowerShell)
```powershell
cd donmulwon2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m donmulwon2.app
```

## 현재 구현
- 16:9 가로형 데스크톱 레이아웃
- 단일 너구리 애널리스트 캐릭터 영역(원화 교체용 자리)
- KOSPI/KOSDAQ 시장 요약 영역
- RSI/MACD/10일선 필수 신호 조건 표시
- 종목 발굴, 차트 분석, 애널리스트 보고서 탭
- 실제 데이터가 연결되지 않았음을 명시

## 아직 구현하지 않은 기능
- 국내 주식 실시간/일봉 데이터 수집
- RSI(10/14), MACD(5/10/9) 실제 계산
- 10일선 상향 돌파 감지 및 알림
- 매물대/볼린저 밴드/거래량 분석
- 240일선 위험 표시
- 종목 설명, 진입/익절/손절 산출

이 프로젝트는 자동매매를 수행하지 않습니다.
