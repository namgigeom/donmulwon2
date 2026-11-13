import math
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget, QVBoxLayout


CANVAS_W = 1672
CANVAS_H = 941
FOOTER_H = 54


class MainScreen(QWidget):
    """Approved pixel-art background with a small live, interactive overlay."""

    TABS = ["시장 현황", "종목 발굴", "차트 분석", "애널리스트"]

    def __init__(self, image_path: Path):
        super().__init__()
        self.image = QPixmap(str(image_path))
        if self.image.isNull():
            raise RuntimeError(f"메인 화면 이미지를 읽을 수 없습니다: {image_path}")

        self.started_at = datetime.now()
        self.active_tab = 0
        self.tick = 0
        self.scroll_offset = 0
        self.setMouseTracking(True)
        self.setMinimumSize(1000, 563)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)
        self.timer.start(80)

    def advance_animation(self):
        self.tick += 1
        self.scroll_offset = (self.scroll_offset + 2) % 1100
        self.update()

    def _layout_image(self):
        scaled = self.image.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return scaled, x, y, scaled.width() / CANVAS_W

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.fillRect(self.rect(), QColor("#151b19"))

        scaled, x, y, factor = self._layout_image()
        painter.drawPixmap(x, y, scaled)

        # Draw overlays in the original artwork's 1672x941 coordinate space.
        painter.save()
        painter.translate(x, y)
        painter.scale(factor, factor)
        self._draw_live_footer(painter)
        painter.restore()

    def _draw_live_footer(self, painter):
        y = CANVAS_H - FOOTER_H
        painter.fillRect(0, y, CANVAS_W, FOOTER_H, QColor(20, 27, 25, 238))
        painter.setPen(QColor("#a98b5c"))
        painter.drawLine(0, y, CANVAS_W, y)

        # Blinking connection indicator: intentionally marked DEMO until market
        # data providers are connected, so sample values cannot be mistaken for quotes.
        pulse = 150 + int(90 * (0.5 + 0.5 * math.sin(self.tick / 5)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(91, 190, 123, pulse))
        painter.drawEllipse(22, y + 19, 12, 12)

        painter.setPen(QColor("#d9c49d"))
        painter.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        painter.drawText(44, y + 34, "DONMULWON 2  ·  DEMO MODE")

        # Real local clock.
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        painter.setPen(QColor("#eee4d1"))
        painter.setFont(QFont("Consolas", 11))
        painter.drawText(1320, y + 34, now)

        # Animated ticker. These are labels/status only, not fabricated stock prices.
        message = "  ◆  MARKET DATA CONNECTING  ·  RSI(10/14)  ·  MACD(5/10/9)  ·  10-DAY MA BREAKOUT  ·  NO LIVE QUOTES YET  ◆  "
        painter.setClipRect(300, y + 8, 980, FOOTER_H - 12)
        painter.setPen(QColor("#d5b77e"))
        painter.setFont(QFont("Malgun Gothic", 10))
        text_width = painter.fontMetrics().horizontalAdvance(message)
        start = 300 - self.scroll_offset
        while start < 1280:
            painter.drawText(start, y + 33, message)
            start += text_width + 70
        painter.setClipping(False)

        # Clickable section selector.
        tab_x = 22
        tab_y = 8
        tab_w = 130
        for index, label in enumerate(self.TABS):
            left = tab_x + index * (tab_w + 8)
            active = index == self.active_tab
            painter.setPen(QColor("#e7c98e") if active else QColor("#9d9a8b"))
            painter.setBrush(QColor(87, 66, 42, 220) if active else QColor(25, 31, 29, 215))
            painter.drawRoundedRect(left, tab_y, tab_w, 30, 5, 5)
            painter.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold if active else QFont.Weight.Normal))
            painter.drawText(left, tab_y, tab_w, 30, Qt.AlignmentFlag.AlignCenter, label)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        _, x, y, factor = self._layout_image()
        px = (event.position().x() - x) / factor
        py = (event.position().y() - y) / factor
        if 8 <= py <= 38 and 22 <= px <= 22 + 4 * 138:
            index = int((px - 22) // 138)
            if 0 <= index < len(self.TABS):
                self.active_tab = index
                self.update()
                return
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2")
        self.setMinimumSize(1000, 563)

        project_root = Path(__file__).resolve().parent
        candidates = [
            project_root / "assets" / "donmulwon2_main_screen.png",
            project_root.parent / "assets" / "donmulwon2_main_screen.png",
        ]
        image_path = next((path for path in candidates if path.exists()), candidates[0])

        if not image_path.exists():
            central = QWidget()
            layout = QVBoxLayout(central)
            message = QLabel(
                "메인 화면 이미지 파일을 찾을 수 없습니다.\\n\\n"
                "assets/donmulwon2_main_screen.png 또는\\n"
                "donmulwon2/assets/donmulwon2_main_screen.png\\n"
                "위 경로에 이미지 파일을 넣어주세요."
            )
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message.setStyleSheet(
                "color:#f2ead8;background:#222a27;font-size:16px;padding:32px;"
            )
            layout.addWidget(message)
            self.setCentralWidget(central)
            self.resize(1000, 563)
            return

        self.setCentralWidget(MainScreen(image_path))
        self.resize(1648, 928)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
