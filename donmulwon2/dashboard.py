"""DONMULWON 2: data is painted into the original pixel-art interface.

The artwork is the UI. No floating panels or independent dashboard windows are
created; only the artwork's existing information surfaces are repainted.
"""
from __future__ import annotations

import math
import random
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QLinearGradient
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox, QInputDialog

from .workers import AnalysisWorker

CANVAS_W, CANVAS_H = 1672, 941


def _fmt_num(value, digits=2):
    try:
        return f"{float(value):,.{digits}f}" if value is not None else "—"
    except (TypeError, ValueError):
        return "—"


def _fmt_money(value):
    try:
        return f"{int(value):,}" if value is not None else "—"
    except (TypeError, ValueError):
        return "—"


def _fmt_flow(value):
    if value is None:
        return "데이터 없음"
    n = int(value)
    unit = "조" if abs(n) >= 1_000_000_000_000 else "억"
    amount = n / (1_000_000_000_000 if unit == "조" else 100_000_000)
    return f"{amount:+.1f}{unit}"


class Dashboard(QWidget):
    """Single-canvas interface that preserves the supplied pixel-art composition."""

    def __init__(self, image_path: Path):
        super().__init__()
        self.image = QPixmap(str(image_path))
        if self.image.isNull():
            raise RuntimeError(f"메인 이미지 읽기 실패: {image_path}")
        self.setMinimumSize(1000, 563)
        self.setMouseTracking(True)
        self._busy = False
        self._threads = []
        self._workers = []
        self.market_data = {}
        self.scan_data = {}
        self.analysis = {}
        self.progress = (0, 0, "")
        self.status = "KRX 데이터 연결 중"
        self.last_update = ""
        self.active_market = "KOSPI"
        self.clock = QTimer(self)
        self.clock.timeout.connect(self.update)
        self.clock.start(1000)
        QTimer.singleShot(500, self._refresh_market)

    # ---- pixel-art painting helpers -------------------------------------------------
    def _font(self, size=16, bold=False, family="Malgun Gothic"):
        font = QFont(family)
        font.setPixelSize(size)
        font.setBold(bold)
        return font

    def _text(self, p, x, y, text, size=16, color="#f7e7c8", bold=False,
              align=Qt.AlignmentFlag.AlignLeft):
        p.setFont(self._font(size, bold))
        p.setPen(QColor(color))
        p.drawText(QRectF(x, y-size-2, 420, size+8), align, str(text))

    def _patch(self, p, rect, base, seed=17, spread=7, tile=3):
        """Small pixel-grain repaint, constrained to existing illustrated panels."""
        x, y, w, h = map(int, rect)
        rng = random.Random(seed)
        c = QColor(base)
        for yy in range(y, y+h, tile):
            for xx in range(x, x+w, tile):
                delta = rng.randint(-spread, spread)
                shade = QColor(max(0, min(255, c.red()+delta)),
                               max(0, min(255, c.green()+delta)),
                               max(0, min(255, c.blue()+delta)))
                p.fillRect(xx, yy, min(tile, x+w-xx), min(tile, y+h-yy), shade)

    def _paper_patch(self, p, rect, seed=21):
        self._patch(p, rect, "#f5d7b8", seed, 5, 3)

    def _dark_patch(self, p, rect, seed=31):
        self._patch(p, rect, "#242334", seed, 5, 3)

    def _sparkline(self, p, rect, values, color):
        if not values:
            return
        x, y, w, h = rect
        vals = [float(v) for v in values if v is not None]
        if len(vals) < 2:
            return
        lo, hi = min(vals), max(vals)
        span = max(hi-lo, abs(hi)*0.002, 1e-6)
        path = []
        for i, value in enumerate(vals):
            px = x + i*w/(len(vals)-1)
            py = y+h - (value-lo)/span*h
            path.append(QPointF(px, py))
        p.setPen(QPen(QColor(color), 2))
        for a, b in zip(path, path[1:]):
            p.drawLine(a, b)

    def _candles(self, p, rect, records, compact=False):
        x, y, w, h = rect
        rows = (records or [])[-34 if compact else -48:]
        if len(rows) < 2:
            p.setPen(QColor("#9ba6a6"))
            p.setFont(self._font(10))
            p.drawText(QRectF(x, y, w, h), Qt.AlignmentFlag.AlignCenter,
                       "종목 분석 후 실제 차트 표시")
            return
        def val(row, key):
            try:
                return float(row.get(key))
            except (TypeError, ValueError):
                return None
        highs = [val(r, "고가") for r in rows]
        lows = [val(r, "저가") for r in rows]
        closes = [val(r, "종가") for r in rows]
        valid = [v for v in highs+lows+closes if v is not None]
        if not valid:
            return
        lo, hi = min(valid), max(valid)
        pad = max((hi-lo)*0.08, abs(hi)*0.004, 1)
        lo, hi = lo-pad, hi+pad
        def yy(v):
            return y+h-(v-lo)/(hi-lo)*h
        step = w/len(rows)
        candle_w = max(2, min(7, step*0.55))
        p.setPen(QPen(QColor(105, 104, 121, 100), 1, Qt.PenStyle.DotLine))
        for k in range(1, 4):
            gy = y+h*k/4
            p.drawLine(QPointF(x, gy), QPointF(x+w, gy))
        for i, row in enumerate(rows):
            op, cl = val(row, "시가"), val(row, "종가")
            low, high = val(row, "저가"), val(row, "고가")
            if None in (op, cl, low, high):
                continue
            cx = x+(i+0.5)*step
            color = QColor("#e36f68" if cl >= op else "#75a9cf")
            p.setPen(QPen(color, 1))
            p.drawLine(QPointF(cx, yy(high)), QPointF(cx, yy(low)))
            top, bottom = min(yy(op), yy(cl)), max(yy(op), yy(cl))
            p.fillRect(QRectF(cx-candle_w/2, top, candle_w, max(2, bottom-top)), color)
        for key, color in (("MA10", "#f1c66e"), ("MA20", "#72c2a0"), ("MA60", "#b0a0d9")):
            points = []
            for i, row in enumerate(rows):
                v = val(row, key)
                if v is not None:
                    points.append(QPointF(x+(i+0.5)*step, yy(v)))
                else:
                    points.append(None)
            p.setPen(QPen(QColor(color), 1 if compact else 1.5))
            previous = None
            for point in points:
                if point is not None and previous is not None:
                    p.drawLine(previous, point)
                previous = point

    def _draw_background(self, p):
        p.fillRect(self.rect(), QColor("#17141c"))
        scale = min(self.width()/CANVAS_W, self.height()/CANVAS_H)
        w, h = int(CANVAS_W*scale), int(CANVAS_H*scale)
        self._scale = scale
        self._offset = ((self.width()-w)/2, (self.height()-h)/2)
        target = QRectF(self._offset[0], self._offset[1], w, h)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.drawPixmap(target, self.image, QRectF(self.image.rect()))

    def paintEvent(self, event):
        p = QPainter(self)
        self._draw_background(p)
        ox, oy = self._offset
        p.save()
        p.translate(ox, oy)
        p.scale(self._scale, self._scale)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._paint_top(p)
        self._paint_bulletin(p)
        self._paint_checklist(p)
        self._paint_scan_results(p)
        self._paint_charts(p)
        self._paint_status(p)
        p.restore()
        p.end()

    def _paint_top(self, p):
        # Replace only the values already printed inside the four top-bar tiles.
        self._dark_patch(p, (565, 54, 205, 35), 101)
        self._dark_patch(p, (886, 54, 205, 35), 102)
        self._dark_patch(p, (1208, 53, 156, 38), 103)
        self._dark_patch(p, (1470, 53, 130, 38), 104)
        kp = self.market_data.get("KOSPI", {})
        kd = self.market_data.get("KOSDAQ", {})
        self._text(p, 568, 81, f'{_fmt_num(kp.get("index_close"))}  {self._signed_pct(kp.get("index_change"))}',
                   18, self._change_color(kp.get("index_change")), True)
        self._text(p, 890, 81, f'{_fmt_num(kd.get("index_close"))}  {self._signed_pct(kd.get("index_change"))}',
                   18, self._change_color(kd.get("index_change")), True)
        mood = self._market_mood()
        self._text(p, 1220, 81, mood, 19, "#f4d27e", True)
        self._text(p, 1480, 81, f'{len(self.scan_data.get("matches", []))}건', 19, "#f4d27e", True)

    def _paint_bulletin(self, p):
        # Existing board cards are retained. Their sample figures/text are replaced
        # inside the parchment surfaces; wooden borders, pins and decorations remain.
        self._paper_patch(p, (858, 252, 247, 79), 201)
        self._paper_patch(p, (1130, 252, 245, 79), 202)
        self._paper_patch(p, (858, 369, 250, 138), 203)
        self._paper_patch(p, (1135, 369, 243, 138), 204)
        self._paper_patch(p, (866, 584, 444, 69), 205)

        kp, kd = self.market_data.get("KOSPI", {}), self.market_data.get("KOSDAQ", {})
        self._text(p, 875, 281, _fmt_num(kp.get("index_close")), 27, "#251d1a", True)
        self._text(p, 875, 319, self._signed_pct(kp.get("index_change")), 22,
                   self._change_color(kp.get("index_change")), True)
        self._text(p, 1150, 281, _fmt_num(kd.get("index_close")), 27, "#251d1a", True)
        self._text(p, 1150, 319, self._signed_pct(kd.get("index_change")), 22,
                   self._change_color(kd.get("index_change")), True)
        self._sparkline(p, (1000, 267, 90, 48), kp.get("index_history", []), "#c94f4b")
        self._sparkline(p, (1260, 267, 100, 48), kd.get("index_history", []), "#315da8")

        # These cards are deliberately repurposed for available KRX breadth/flows.
        # No unsupported sector performance is fabricated.
        self._text(p, 895, 409, "시장 상승 현황", 19, "#30241d", True)
        self._text(p, 895, 448, f'상승 종목   {kp.get("advancers", "—"):,}' if isinstance(kp.get("advancers"), int) else "상승 종목   —",
                   17, "#267c45", True)
        self._text(p, 895, 482, f'하락 종목   {kp.get("decliners", "—"):,}' if isinstance(kp.get("decliners"), int) else "하락 종목   —",
                   17, "#bd4646", True)
        self._text(p, 1167, 409, "투자자 순매수", 19, "#30241d", True)
        forflows = (kp.get("investor_flows") or {}).get("values", {})
        self._text(p, 1167, 448, f'외국인  {_fmt_flow(forflows.get("외국인"))}', 17, "#315da8", True)
        self._text(p, 1167, 482, f'개인    {_fmt_flow(forflows.get("개인"))}', 17, "#315da8", True)

        self._text(p, 900, 618, self._summary_line(), 17, "#193b69", True)
        self._text(p, 900, 645, self._summary_second_line(), 16, "#193b69", True)
        date = self.last_update or "거래일 확인 중"
        self._text(p, 1250, 651, date[-5:], 10, "#735b48", False)

    def _paint_checklist(self, p):
        # Existing checklist frame and heading stay untouched.
        checks = (self.analysis.get("signal") or {}).get("checks", {})
        keys = ("rsi_cross_and_rising", "macd_cross_and_rising", "ma10_breakout")
        labels = ("RSI(10) / RSI(14) 상향 교차", "MACD 상승 전환", "10일 이동평균선 돌파")
        for i, (key, label) in enumerate(zip(keys, labels)):
            y = 780 + i*39
            self._dark_patch(p, (48, y-20, 355, 28), 310+i)
            ok = checks.get(key)
            box = QColor("#3eaa65" if ok else "#756b68" if ok is False else "#6a6870")
            p.fillRect(51, y-15, 27, 27, box)
            p.setPen(QPen(QColor("#f4f0df"), 3))
            if ok:
                p.drawLine(QPointF(57, y-2), QPointF(63, y+4))
                p.drawLine(QPointF(63, y+4), QPointF(73, y-8))
            elif ok is False:
                p.drawLine(QPointF(58, y-8), QPointF(71, y+5))
                p.drawLine(QPointF(71, y-8), QPointF(58, y+5))
            self._text(p, 91, y+4, label, 17, "#f0eee8", True)
        if not self.analysis:
            self._text(p, 92, 870, "종목 분석을 실행하면 조건별 결과가 표시됩니다.", 12, "#c7c3c7")

    def _paint_scan_results(self, p):
        # Keep the original panel art and its progress-bar frame.
        self._dark_patch(p, (490, 773, 410, 47), 401)
        self._dark_patch(p, (490, 853, 410, 22), 402)
        if self._busy and self.progress[1]:
            current, total, ticker = self.progress
            pct = current/total
            status = f"전 종목 검사 중  {current:,}/{total:,}  ({pct*100:.0f}%)"
            self._text(p, 510, 802, status, 16, "#f4e8d5", True)
            self._text(p, 510, 827, ticker, 12, "#c7c3d0")
            p.fillRect(QRectF(514, 829, 350*pct, 17), QColor("#61bd78"))
        elif self.scan_data:
            matches = self.scan_data.get("matches", [])
            self._text(p, 510, 801, f'검색 {self.scan_data.get("scanned", 0):,}종목 · 조건 충족 {len(matches)}종목',
                       16, "#f4e8d5", True)
            for i, item in enumerate(matches[:2]):
                self._text(p, 510, 828+i*22,
                           f'{item.get("name", "")}  {item.get("ticker", "")}  {_fmt_money(item.get("latest", {}).get("close"))}원',
                           13, "#d9e4d7")
        else:
            self._text(p, 510, 803, "오른쪽 [종목 스캔]을 눌러 KOSPI/KOSDAQ을 검색하세요.", 14, "#e7dfd2")
            self._text(p, 510, 830, "조건: RSI 교차 · MACD 상향 교차 · 종가 10일선 돌파", 12, "#c7c3d0")
        self._text(p, 510, 867, self.status[:48], 11, "#b8b4c2")

    def _paint_charts(self, p):
        # Monitor screen in the artwork, and the lower chart viewport.
        self._dark_patch(p, (552, 466, 183, 111), 501)
        records = self.analysis.get("ohlcv", [])
        self._candles(p, (558, 475, 170, 90), records, compact=True)
        self._dark_patch(p, (951, 750, 385, 130), 502)
        self._candles(p, (957, 755, 373, 119), records, compact=False)
        if self.analysis:
            latest = self.analysis.get("latest", {})
            title = f'{self.analysis.get("name", "")}  {_fmt_money(latest.get("close"))}원'
            self._text(p, 962, 741, title, 11, "#f3d28a", True)

    def _paint_status(self, p):
        # A tiny status line in the existing result panel, not a new footer widget.
        self._text(p, 780, 867, datetime.now().strftime("%H:%M:%S"), 10, "#b8b4c2")

    def _signed_pct(self, value):
        if value is None:
            return "—"
        try:
            return f'{"▲" if float(value) >= 0 else "▼"} {float(value):+.2f}%'
        except (TypeError, ValueError):
            return "—"

    def _change_color(self, value):
        try:
            return "#d44c48" if float(value) >= 0 else "#315da8"
        except (TypeError, ValueError):
            return "#d8c9a7"

    def _market_mood(self):
        item = self.market_data.get("KOSPI", {})
        change = item.get("index_change")
        if change is None:
            return "집계 중"
        try:
            return "강세" if float(change) > 0.25 else "약세" if float(change) < -0.25 else "보합"
        except (TypeError, ValueError):
            return "집계 중"

    def _summary_line(self):
        item = self.market_data.get("KOSPI", {})
        adv, dec = item.get("advancers"), item.get("decliners")
        if adv is None or dec is None:
            return "KRX 시장 데이터 수신을 기다리는 중입니다."
        return f'KOSPI 상승 {adv:,}종목 · 하락 {dec:,}종목'
    
    def _summary_second_line(self):
        item = self.market_data.get("KOSPI", {})
        flows = (item.get("investor_flows") or {}).get("values", {})
        foreign, personal = flows.get("외국인"), flows.get("개인")
        if foreign is None and personal is None:
            return "투자자별 수급 데이터는 확인되는 항목만 표시합니다."
        return f'외국인 {_fmt_flow(foreign)}  /  개인 {_fmt_flow(personal)} 순매수'

    # ---- interaction zones are the artwork's own illustrated buttons ---------------
    def mousePressEvent(self, event):
        point = self._to_canvas(event.position().x(), event.position().y())
        if point is None:
            return
        x, y = point
        if 1480 <= x <= 1638:
            if 145 <= y <= 286:
                self._refresh_market()
            elif 290 <= y <= 431:
                self._scan_market()
            elif 435 <= y <= 530:
                self._prompt_ticker()
            elif 535 <= y <= 630:
                QMessageBox.information(self, "알림 설정", "현재 버전에서는 매수 신호 건수와 분석 결과를 화면에 표시합니다. 가격 알림은 아직 구현되지 않았습니다.")
            elif 635 <= y <= 724:
                self.active_market = "KOSDAQ" if self.active_market == "KOSPI" else "KOSPI"
                self.status = f"종목 스캔 시장: {self.active_market}"
                self.update()
            elif 730 <= y <= 823:
                self.window().close()

    def _to_canvas(self, x, y):
        scale = getattr(self, "_scale", 1)
        ox, oy = getattr(self, "_offset", (0, 0))
        cx, cy = (x-ox)/scale, (y-oy)/scale
        if 0 <= cx <= CANVAS_W and 0 <= cy <= CANVAS_H:
            return cx, cy
        return None

    def _prompt_ticker(self):
        ticker, ok = QInputDialog.getText(self, "종목 분석", "한국 주식 종목코드 6자리:")
        if ok and ticker.strip():
            ticker = ticker.strip()
            if len(ticker) != 6 or not ticker.isdigit():
                QMessageBox.warning(self, "종목코드 확인", "종목코드 6자리를 입력해 주세요.")
                return
            self._run_worker("ticker", ticker=ticker)

    # ---- background work -------------------------------------------------------------
    def _run_worker(self, task, ticker="", market=None):
        if self._busy:
            return
        self._busy = True
        self.status = "KRX 데이터 수집 중"
        self.progress = (0, 0, "")
        thread = QThread(self)
        worker = AnalysisWorker(task, ticker=ticker, market=market or self.active_market)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_worker_finished)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._worker_stopped)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()
        self.update()

    def _worker_stopped(self):
        self._busy = False
        self._threads.clear()
        self._workers.clear()
        self.update()

    def _refresh_market(self):
        self._run_worker("dashboard")

    def _scan_market(self):
        self._run_worker("scan", market=self.active_market)

    def _on_progress(self, current, total, ticker):
        self.progress = (current, total, ticker)
        self.status = f"{self.active_market} 전 종목 검색"
        self.update()

    def _on_worker_finished(self, data):
        if "markets" in data:
            self.market_data = data.get("markets", {})
            self.last_update = data.get("date", "")
            self.status = "시장 게시판 갱신 완료"
        elif "ohlcv" in data:
            self.analysis = data
            self.status = f'{data.get("name", "")} 분석 완료'
        elif "matches" in data:
            self.scan_data = data
            self.status = f'{data.get("market", "")} 검색 완료 · 오류 {data.get("error_count", 0)}건'
        self.update()

    def _on_worker_failed(self, message):
        self.status = f"데이터 수집 실패: {message}"
        QMessageBox.warning(self, "돈물원 데이터 오류", message)
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2")
        self.setMinimumSize(1000, 563)
        root = Path(__file__).resolve().parent
        candidates = [
            root.parent / "assets" / "donmulwon2_main_screen.png",
            root / "assets" / "donmulwon2_main_screen.png",
        ]
        image_path = next((path for path in candidates if path.exists()), candidates[0])
        if not image_path.exists():
            raise FileNotFoundError("assets/donmulwon2_main_screen.png 파일을 찾을 수 없습니다.")
        self.setCentralWidget(Dashboard(image_path))
        self.resize(1672, 941)


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
