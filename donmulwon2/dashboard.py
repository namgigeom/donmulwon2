"""DONMULWON 2 functional dashboard: live data overlays on the approved static artwork."""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QTableWidget, QComboBox,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView
)

from .workers import AnalysisWorker


CANVAS_W, CANVAS_H = 1672, 941
FOOTER_H = 54


def money(value):
    if value is None:
        return "—"
    try:
        return f"{int(value):,}원"
    except (ValueError, TypeError):
        return "—"


def number(value, digits=2):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}"
    except (ValueError, TypeError):
        return "—"


class Panel(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setStyleSheet("""
            QFrame#panel {
                background-color: rgba(20, 29, 27, 226);
                border: 1px solid rgba(196, 164, 111, 190);
                border-radius: 8px;
            }
            QLabel { color: #eee7d8; background: transparent; }
            QLabel#panelTitle { color: #d9b77d; font-size: 13px; font-weight: 700; }
            QLabel#muted { color: #a9b2a9; font-size: 10px; }
            QLabel#value { color: #f2e6cd; font-size: 16px; font-weight: 700; }
            QPushButton {
                color: #f3e8d3; background: #35463d; border: 1px solid #9c8056;
                border-radius: 4px; padding: 6px 10px; font-weight: 600;
            }
            QPushButton:hover { background: #49614f; }
            QPushButton:disabled { color: #8c958c; background: #29332e; }
            QLineEdit {
                color: #f5ead7; background: #17211e; border: 1px solid #8f7956;
                border-radius: 4px; padding: 6px;
            }
            QTableWidget {
                color: #eee7d8; background: rgba(12, 19, 17, 220);
                gridline-color: #435149; border: 0;
                selection-background-color: #526b55;
            }
            QHeaderView::section {
                color: #d9b77d; background: #26332d; border: 0;
                padding: 5px; font-weight: 700;
            }
            QProgressBar {
                color: #eee7d8; background: #17211e; border: 1px solid #6d765f;
                border-radius: 4px; text-align: center;
            }
            QProgressBar::chunk { background: #78966e; }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(7)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        self.layout.addWidget(heading)


class TechnicalChart(QWidget):
    """Native Qt chart: candles, moving averages, RSI and MACD, no chart sample data."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.setMinimumHeight(300)

    def set_records(self, records):
        self.records = records or []
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(13, 20, 18, 245))
        bounds = self.rect().adjusted(34, 16, -12, -18)
        p.setPen(QColor("#718077"))
        p.setFont(QFont("Malgun Gothic", 8))
        if len(self.records) < 3:
            p.drawText(bounds, Qt.AlignmentFlag.AlignCenter, "종목을 검색하면 실제 일봉 차트가 표시됩니다.")
            return

        rows = self.records[-65:]
        prices = [float(r.get("종가", 0) or 0) for r in rows if r.get("종가") is not None]
        if not prices:
            p.drawText(bounds, Qt.AlignmentFlag.AlignCenter, "유효한 종가 데이터가 없습니다.")
            return
        lows = [float(r.get("저가", r.get("종가", 0)) or 0) for r in rows]
        highs = [float(r.get("고가", r.get("종가", 0)) or 0) for r in rows]
        lo, hi = min(lows), max(highs)
        span = max(hi - lo, max(hi * 0.015, 1))
        chart_h = bounds.height() * 0.66
        chart = QRectF(bounds.left(), bounds.top(), bounds.width(), chart_h)
        rsi_area = QRectF(bounds.left(), chart.bottom() + 12, bounds.width(), bounds.height() * 0.12)
        macd_area = QRectF(bounds.left(), rsi_area.bottom() + 12, bounds.width(), bounds.height() * 0.15)

        p.setPen(QPen(QColor(83, 101, 91, 130), 1, Qt.PenStyle.DotLine))
        for i in range(5):
            y = chart.top() + chart.height() * i / 4
            p.drawLine(QPointF(chart.left(), y), QPointF(chart.right(), y))
        p.setPen(QColor("#b9c2b5"))
        p.drawText(QRectF(0, chart.top(), 30, 16), Qt.AlignmentFlag.AlignRight, f"{hi:,.0f}")
        p.drawText(QRectF(0, chart.bottom()-14, 30, 16), Qt.AlignmentFlag.AlignRight, f"{lo:,.0f}")

        def px(i):
            return chart.left() + (i + 0.5) * chart.width() / len(rows)
        def py(value):
            return chart.bottom() - (value - lo) / span * chart.height()

        candle_w = max(2.0, chart.width() / len(rows) * 0.55)
        for i, row in enumerate(rows):
            try:
                op = float(row["시가"]); cl = float(row["종가"])
                low = float(row["저가"]); high = float(row["고가"])
            except (KeyError, TypeError, ValueError):
                continue
            up = cl >= op
            color = QColor("#e47770" if up else "#70a8c8")
            p.setPen(QPen(color, 1))
            p.drawLine(QPointF(px(i), py(high)), QPointF(px(i), py(low)))
            top, bottom = min(py(op), py(cl)), max(py(op), py(cl))
            p.fillRect(QRectF(px(i)-candle_w/2, top, candle_w, max(1.5, bottom-top)), color)

        for key, color in (("MA10", "#e7c46c"), ("MA20", "#79b9a0"), ("MA60", "#a99bd2")):
            path = QPainterPath()
            started = False
            for i, row in enumerate(rows):
                value = row.get(key)
                if value is None:
                    started = False
                    continue
                try:
                    point = QPointF(px(i), py(float(value)))
                except (ValueError, TypeError):
                    continue
                if not started:
                    path.moveTo(point); started = True
                else:
                    path.lineTo(point)
            p.setPen(QPen(QColor(color), 1.4))
            p.drawPath(path)

        p.setPen(QColor("#d9b77d"))
        p.drawText(QRectF(rsi_area.left(), rsi_area.top()-11, 70, 12), "RSI(10/14)")
        rsi_values = [r.get("RSI10") for r in rows]
        rsi_path = QPainterPath()
        started = False
        for i, value in enumerate(rsi_values):
            if value is None:
                started = False; continue
            point = QPointF(px(i), rsi_area.bottom() - max(0, min(100, float(value))) / 100 * rsi_area.height())
            if not started:
                rsi_path.moveTo(point); started = True
            else:
                rsi_path.lineTo(point)
        p.setPen(QPen(QColor("#d9b77d"), 1.3)); p.drawPath(rsi_path)
        y50 = rsi_area.top() + rsi_area.height()/2
        p.setPen(QPen(QColor(105, 119, 108, 120), 1, Qt.PenStyle.DotLine))
        p.drawLine(QPointF(rsi_area.left(), y50), QPointF(rsi_area.right(), y50))

        p.setPen(QColor("#d9b77d"))
        p.drawText(QRectF(macd_area.left(), macd_area.top()-11, 80, 12), "MACD HIST")
        hist = [r.get("MACD_HIST") for r in rows]
        valid = [abs(float(v)) for v in hist if v is not None]
        max_abs = max(valid) if valid else 1
        zero_y = macd_area.center().y()
        p.setPen(QPen(QColor("#6c7c70"), 1))
        p.drawLine(QPointF(macd_area.left(), zero_y), QPointF(macd_area.right(), zero_y))
        for i, value in enumerate(hist):
            if value is None: continue
            val = float(value)
            bar_h = abs(val) / max_abs * macd_area.height() * 0.43
            color = QColor("#d87970" if val >= 0 else "#6fa6c4")
            p.fillRect(QRectF(px(i)-candle_w/2, zero_y-bar_h if val >= 0 else zero_y,
                              candle_w, max(1, bar_h)), color)


class Dashboard(QWidget):
    def __init__(self, image_path: Path):
        super().__init__()
        self.image = QPixmap(str(image_path))
        if self.image.isNull():
            raise RuntimeError(f"메인 이미지 읽기 실패: {image_path}")
        self.tick = 0
        self._threads = []
        self._workers = []
        self._busy = False
        self._build_panels()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(1000)
        QTimer.singleShot(700, self._refresh_market)

    def _build_panels(self):
        self.market_panel = Panel("MARKET BULLETIN  /  KRX")
        self.market_status = QLabel("시장 데이터 연결 대기")
        self.market_status.setObjectName("muted")
        self.market_panel.layout.addWidget(self.market_status)
        self.market_values = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(9)
        for i, (key, label) in enumerate([
            ("kospi", "KOSPI"), ("kosdaq", "KOSDAQ"),
            ("breadth", "상승 / 하락"), ("value", "거래대금"),
            ("flow", "투자자 수급"), ("date", "기준 거래일"),
        ]):
            name = QLabel(label); name.setObjectName("muted")
            value = QLabel("—"); value.setObjectName("value")
            self.market_values[key] = value
            grid.addWidget(name, (i//2)*2, i%2)
            grid.addWidget(value, (i//2)*2+1, i%2)
        self.market_panel.layout.addLayout(grid)
        self.market_summary = QLabel("시장 한줄 요약: 실제 데이터 수신 전")
        self.market_summary.setWordWrap(True)
        self.market_panel.layout.addWidget(self.market_summary)
        self.market_panel.layout.addStretch(1)

        self.scan_panel = Panel("SCREENER  /  RSI · MACD · MA10")
        self.scan_hint = QLabel("세 가지 필수 조건을 모두 충족한 종목만 후보로 표시합니다.")
        self.scan_hint.setObjectName("muted")
        self.scan_panel.layout.addWidget(self.scan_hint)
        self.scan_table = QTableWidget(0, 5)
        self.scan_table.setHorizontalHeaderLabels(["종목", "종가", "RSI10", "MACD", "조건"])
        self.scan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.scan_table.verticalHeader().setVisible(False)
        self.scan_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.scan_table.cellClicked.connect(self._select_scan_row)
        self.scan_panel.layout.addWidget(self.scan_table, 1)
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.scan_panel.layout.addWidget(self.scan_progress)
        self.scan_status = QLabel("검색 대기")
        self.scan_status.setObjectName("muted")
        self.scan_panel.layout.addWidget(self.scan_status)

        self.detail_panel = Panel("ANALYST DESK  /  STOCK REPORT")
        controls = QHBoxLayout()
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("종목코드 6자리 (예: 005930)")
        self.ticker_input.returnPressed.connect(self._analyze_ticker)
        self.search_button = QPushButton("종목 분석")
        self.search_button.clicked.connect(self._analyze_ticker)
        self.market_selector = QComboBox()
        self.market_selector.addItems(["KOSPI", "KOSDAQ"])
        self.scan_button = QPushButton("시장 검색")
        self.scan_button.clicked.connect(self._scan_market)
        self.refresh_button = QPushButton("시장 갱신")
        self.refresh_button.clicked.connect(self._refresh_market)
        controls.addWidget(self.ticker_input, 2)
        controls.addWidget(self.search_button)
        self.detail_panel.layout.addLayout(controls)
        scan_controls = QHBoxLayout()
        scan_controls.addWidget(self.market_selector)
        scan_controls.addWidget(self.scan_button)
        scan_controls.addWidget(self.refresh_button)
        self.detail_panel.layout.addLayout(scan_controls)

        self.stock_title = QLabel("종목을 검색하면 분석 결과가 표시됩니다.")
        self.stock_title.setObjectName("value")
        self.detail_panel.layout.addWidget(self.stock_title)
        self.stock_meta = QLabel("종목코드 · 거래일 · 종가 · 등락률")
        self.stock_meta.setObjectName("muted")
        self.detail_panel.layout.addWidget(self.stock_meta)
        self.signal_labels = {}
        signal_grid = QGridLayout()
        for i, (key, title) in enumerate([
            ("rsi", "RSI 10 / 14"), ("macd", "MACD / SIGNAL"),
            ("ma10", "10일 이동평균"), ("ma240", "240일 이동평균"),
            ("volume", "거래량 / 20일 평균"), ("bb", "볼린저 밴드"),
        ]):
            lab = QLabel(title); lab.setObjectName("muted")
            val = QLabel("—"); val.setObjectName("value")
            self.signal_labels[key] = val
            signal_grid.addWidget(lab, (i//2)*2, i%2)
            signal_grid.addWidget(val, (i//2)*2+1, i%2)
        self.detail_panel.layout.addLayout(signal_grid)
        self.condition_text = QLabel("필수 조건: RSI 교차 · MACD 교차 · 10일선 돌파")
        self.condition_text.setWordWrap(True)
        self.detail_panel.layout.addWidget(self.condition_text)
        self.chart = TechnicalChart()
        self.detail_panel.layout.addWidget(self.chart, 1)
        self.report_text = QLabel("목표·손절 가격은 변동성/지지저항 검증을 붙인 뒤 표시합니다. 검증 전 임의 가격은 제시하지 않습니다.")
        self.report_text.setWordWrap(True)
        self.report_text.setObjectName("muted")
        self.detail_panel.layout.addWidget(self.report_text)

        self.footer_status = QLabel("● KRX DATA NOT CONNECTED")
        self.footer_status.setStyleSheet("color:#d9b77d;background:rgba(16,23,21,220);padding:8px;")
        self.footer_clock = QLabel("")
        self.footer_clock.setStyleSheet("color:#eee4d1;background:rgba(16,23,21,220);padding:8px;")

        self.market_panel.setParent(self)
        self.scan_panel.setParent(self)
        self.detail_panel.setParent(self)
        self.footer_status.setParent(self)
        self.footer_clock.setParent(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        sx, sy = self.width()/CANVAS_W, self.height()/CANVAS_H
        # Place functional overlays in the bulletin and right-side data desk zones.
        self.market_panel.setGeometry(int(48*sx), int(116*sy), int(430*sx), int(335*sy))
        self.scan_panel.setGeometry(int(48*sx), int(465*sy), int(570*sx), int(380*sy))
        self.detail_panel.setGeometry(int(1110*sx), int(100*sy), int(520*sx), int(745*sy))
        self.footer_status.setGeometry(int(18*sx), int((CANVAS_H-FOOTER_H)*sy), int(380*sx), int(FOOTER_H*sy))
        self.footer_clock.setGeometry(int(1320*sx), int((CANVAS_H-FOOTER_H)*sy), int(330*sx), int(FOOTER_H*sy))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.fillRect(self.rect(), QColor("#151b19"))
        scaled = self.image.scaled(self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.FastTransformation)
        p.drawPixmap(0, 0, scaled)

    def _animate(self):
        self.tick += 1
        self.footer_clock.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))

    def _run_worker(self, task, ticker="", market="KOSPI"):
        if self._busy:
            return
        self._busy = True
        for button in (self.search_button, self.scan_button, self.refresh_button):
            button.setEnabled(False)
        thread = QThread(self)
        worker = AnalysisWorker(task, ticker=ticker, market=market)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_worker_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._worker_stopped)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()
        self.footer_status.setText("● KRX DATA FETCHING")

    def _worker_stopped(self):
        self._busy = False
        for button in (self.search_button, self.scan_button, self.refresh_button):
            button.setEnabled(True)
        self._threads.clear()
        self._workers.clear()

    def _refresh_market(self):
        self._run_worker("dashboard")

    def _analyze_ticker(self):
        ticker = self.ticker_input.text().strip()
        if len(ticker) != 6 or not ticker.isdigit():
            QMessageBox.warning(self, "종목코드 확인", "한국 주식 종목코드 6자리를 입력해 주세요.")
            return
        self._run_worker("ticker", ticker=ticker)

    def _scan_market(self):
        self.scan_progress.setValue(0)
        self._run_worker("scan", market=self.market_selector.currentText())

    def _on_progress(self, current, total, ticker):
        self.scan_progress.setValue(int(current / max(total, 1) * 100))
        self.scan_status.setText(f"{self.market_selector.currentText()} 전 종목 검사 중: {current:,}/{total:,} · {ticker}")

    def _on_worker_finished(self, data):
        self.footer_status.setText("● KRX DATA RECEIVED")
        if "markets" in data:
            self._show_market(data)
        elif "ohlcv" in data:
            self._show_analysis(data)
        elif "matches" in data:
            self._show_scan(data)

    def _on_worker_failed(self, message):
        self.footer_status.setText("● DATA ERROR")
        QMessageBox.warning(self, "데이터 수집 실패", message)

    def _show_market(self, data):
        kospi, kosdaq = data.get("markets", {}).get("KOSPI"), data.get("markets", {}).get("KOSDAQ")
        self.market_status.setText(f"KRX 일봉 기준 · {data.get('date', '—')}")
        if kospi:
            self.market_values["kospi"].setText(f"{number(kospi.get('index_close'), 2)}  ({number(kospi.get('index_change'), 2)}%)")
            self.market_values["breadth"].setText(f'{kospi.get("advancers", 0):,} / {kospi.get("decliners", 0):,}')
            self.market_values["value"].setText(_compact_won(kospi.get("trading_value")))
            self.market_values["date"].setText(kospi.get("date", "—"))
            self.market_values["flow"].setText(_flow_label(kospi.get("investor_flows")))
            self.market_summary.setText(kospi.get("one_line_summary", "시장 요약 미수신"))
        if kosdaq:
            self.market_values["kosdaq"].setText(f"{number(kosdaq.get('index_close'), 2)}  ({number(kosdaq.get('index_change'), 2)}%)")

    def _show_analysis(self, data):
        latest, signal = data["latest"], data["signal"]
        self.stock_title.setText(f'{data["name"]}  ·  {data["ticker"]}')
        self.stock_meta.setText(
            f'{data["trading_date"]} 기준  |  종가 {money(latest.get("close"))}  |  등락 {number(latest.get("change_pct"))}%'
        )
        self.signal_labels["rsi"].setText(f'{number(latest.get("rsi10"))} / {number(latest.get("rsi14"))}')
        self.signal_labels["macd"].setText(f'{number(latest.get("macd"), 4)} / {number(latest.get("macd_signal"), 4)}')
        self.signal_labels["ma10"].setText(money(latest.get("ma10")))
        self.signal_labels["ma240"].setText(money(latest.get("ma240")))
        self.signal_labels["volume"].setText(f'{latest.get("volume", 0):,}주')
        self.signal_labels["bb"].setText(
            f'{money(latest.get("bb_lower"))} ~ {money(latest.get("bb_upper"))}'
        )
        checks = signal.get("checks", {})
        labels = [
            ("RSI(10/14) 상향 교차 및 동반 상승", checks.get("rsi_cross_and_rising")),
            ("MACD(5/10/9) 상향 교차 및 상승", checks.get("macd_cross_and_rising")),
            ("종가 10일선 상향 돌파", checks.get("ma10_breakout")),
        ]
        self.condition_text.setText("\n".join(
            f'{"✓" if ok else "✕"}  {label}' for label, ok in labels
        ))
        self.report_text.setText(
            "세 조건 모두 충족: 후보 신호" if signal.get("matched")
            else "현재 봉 기준 필수 조건 미충족. 교차가 발생한 날인지 확인하세요."
        )
        self.chart.set_records(data.get("ohlcv", []))

    def _show_scan(self, data):
        matches = data.get("matches", [])
        self.scan_table.setRowCount(len(matches))
        for row, item in enumerate(matches):
            latest, signal = item["latest"], item["signal"]
            values = [
                f'{item["name"]} ({item["ticker"]})',
                money(latest.get("close")),
                number(latest.get("rsi10")),
                number(latest.get("macd"), 4),
                "3/3 충족",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.scan_table.setItem(row, col, cell)
        self.scan_status.setText(
            f'{data["date"]} · {data["market"]} {data["scanned"]:,}종목 검사 · '
            f'조건 충족 {len(matches)}종목 · 오류 {data["error_count"]}건'
        )
        if not matches:
            self.scan_hint.setText("현재 거래일 기준 세 가지 조건을 모두 만족한 종목이 없습니다.")
        else:
            self.scan_hint.setText("행을 선택하면 해당 종목의 상세 분석을 불러옵니다.")

    def _select_scan_row(self, row, column):
        item = self.scan_table.item(row, 0)
        if not item:
            return
        ticker = item.text().split("(")[-1].replace(")", "").strip()
        if len(ticker) == 6 and ticker.isdigit():
            self.ticker_input.setText(ticker)
            self._analyze_ticker()


def _compact_won(value):
    if value is None: return "—"
    value = int(value)
    if value >= 1_000_000_000_000: return f"{value/1_000_000_000_000:.2f}조원"
    if value >= 100_000_000: return f"{value/100_000_000:.1f}억원"
    return f"{value:,}원"


def _flow_label(data):
    if not data: return "수급 미수신"
    vals = data.get("values", {})
    if not vals: return "수급 미수신"
    preferred = ["외국인", "개인", "연기금", "금융투자", "투신", "보험"]
    chosen = [(key, vals[key]) for key in preferred if key in vals][:2]
    if not chosen:
        chosen = list(vals.items())[:2]
    return " / ".join(f"{k} {v/100_000_000:+.0f}억" for k, v in chosen)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2 · Korean Market Intelligence")
        self.setMinimumSize(1280, 720)
        root = Path(__file__).resolve().parent
        candidates = [root.parent / "assets" / "donmulwon2_main_screen.png",
                      root / "assets" / "donmulwon2_main_screen.png"]
        image_path = next((p for p in candidates if p.exists()), candidates[0])
        if not image_path.exists():
            raise FileNotFoundError(
                "assets/donmulwon2_main_screen.png 파일을 찾을 수 없습니다."
            )
        self.setCentralWidget(Dashboard(image_path))
        self.resize(1600, 900)


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
