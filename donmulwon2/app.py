import sys
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTabWidget, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QSizePolicy
)

# DONMULWON 2 — pixel-art investment office
BG = "#222a27"
WALL = "#d7c7a5"
WALL_DARK = "#b69d76"
WOOD = "#805b3d"
WOOD_DARK = "#503a2c"
INK = "#39352e"
PAPER = "#f0e5c9"
PAPER_INK = "#534633"
PANEL = "#303b36"
PANEL_DARK = "#202a26"
TEXT = "#f2ead8"
MUTED = "#b9b29f"
GOLD = "#e0b96e"
GREEN = "#7fbd91"
RED = "#d47d70"
BORDER = "#657064"


def ui_label(text, size=9, color=TEXT, bold=False):
    w = QLabel(text)
    w.setFont(QFont("Malgun Gothic", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    w.setStyleSheet(f"color:{color}; background:transparent;")
    return w


def make_card(object_name="card"):
    f = QFrame()
    f.setObjectName(object_name)
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f


class PixelOfficeScene(QWidget):
    """A native, resolution-independent pixel-art office illustration."""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(360)
        self.setMinimumHeight(590)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def block(self, p, x, y, w, h, color, unit):
        p.fillRect(int(x * unit), int(y * unit), max(1, int(w * unit)), max(1, int(h * unit)), QColor(color))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        # Work on a 100 x 150 logical pixel canvas.
        u = max(3, min(self.width() // 100, self.height() // 150))
        ox = (self.width() - 100 * u) // 2
        oy = (self.height() - 150 * u) // 2
        p.translate(ox, oy)

        # Warm office wall and floor.
        self.block(p, 0, 0, 100, 150, WALL, u)
        self.block(p, 0, 0, 100, 7, "#c2ad87", u)
        for x in range(4, 100, 12):
            self.block(p, x, 8, 1, 90, "#cfbd9b", u)
        self.block(p, 0, 104, 100, 46, "#9a7654", u)
        for y in range(108, 150, 8):
            self.block(p, 0, y, 100, 1, "#79583e", u)
        for x in range(5, 100, 18):
            self.block(p, x, 108, 1, 42, "#896646", u)

        # Window and tiny city skyline.
        self.block(p, 58, 13, 36, 48, WOOD_DARK, u)
        self.block(p, 60, 15, 32, 44, "#7e9a9a", u)
        self.block(p, 61, 16, 30, 42, "#b5c6b8", u)
        self.block(p, 61, 37, 30, 21, "#e5c98f", u)
        # Distant buildings.
        buildings = [(63, 28, 5, 30), (70, 22, 6, 36), (78, 31, 5, 27), (85, 25, 5, 33)]
        for x, y, w, h in buildings:
            self.block(p, x, y, w, h, "#667c78", u)
            for wy in range(y + 3, 57, 6):
                self.block(p, x + 1, wy, 1, 2, "#e8d39c", u)
                if w > 4:
                    self.block(p, x + 3, wy, 1, 2, "#e8d39c", u)
        self.block(p, 75, 15, 1, 44, WOOD_DARK, u)
        self.block(p, 60, 36, 32, 2, WOOD_DARK, u)
        self.block(p, 56, 11, 40, 3, WOOD, u)
        self.block(p, 56, 61, 40, 3, WOOD, u)

        # Wall clock and framed certificate.
        self.block(p, 9, 13, 13, 13, WOOD_DARK, u)
        self.block(p, 10, 14, 11, 11, PAPER, u)
        self.block(p, 15, 16, 1, 4, INK, u)
        self.block(p, 15, 19, 4, 1, INK, u)
        self.block(p, 29, 15, 17, 21, WOOD_DARK, u)
        self.block(p, 31, 17, 13, 17, PAPER, u)
        self.block(p, 33, 20, 9, 1, "#9b8158", u)
        self.block(p, 33, 24, 7, 1, "#9b8158", u)
        self.block(p, 33, 28, 9, 1, "#9b8158", u)

        # Plant in the corner.
        self.block(p, 7, 83, 13, 11, WOOD_DARK, u)
        self.block(p, 8, 84, 11, 8, "#b8754c", u)
        for x, y in [(9, 77), (13, 73), (17, 78), (6, 80), (15, 82)]:
            self.block(p, x, y, 5, 7, "#52785a", u)
        self.block(p, 12, 80, 2, 6, "#6f9b68", u)

        # Desk silhouette and drawers.
        self.block(p, 17, 96, 69, 7, WOOD_DARK, u)
        self.block(p, 15, 93, 73, 5, "#a77a50", u)
        self.block(p, 19, 103, 5, 35, WOOD_DARK, u)
        self.block(p, 78, 103, 5, 35, WOOD_DARK, u)
        self.block(p, 23, 109, 54, 2, "#9a7049", u)
        self.block(p, 23, 119, 54, 2, "#9a7049", u)
        self.block(p, 48, 112, 5, 2, GOLD, u)

        # Monitor on desk.
        self.block(p, 59, 68, 27, 21, WOOD_DARK, u)
        self.block(p, 61, 70, 23, 17, "#202d2b", u)
        self.block(p, 63, 72, 19, 13, "#263d39", u)
        # Tiny chart on monitor.
        for x, y in [(64, 81), (67, 78), (70, 80), (73, 75), (76, 77), (79, 73)]:
            self.block(p, x, y, 2, 2, GREEN, u)
        self.block(p, 71, 89, 3, 4, WOOD_DARK, u)
        self.block(p, 67, 92, 11, 2, WOOD_DARK, u)

        # Desk lamp.
        self.block(p, 27, 76, 3, 17, WOOD_DARK, u)
        self.block(p, 24, 74, 10, 3, GOLD, u)
        self.block(p, 26, 72, 7, 3, "#e7c77e", u)
        self.block(p, 24, 92, 10, 2, WOOD_DARK, u)

        # Paper stack and coffee mug.
        self.block(p, 39, 89, 12, 2, "#d8cba9", u)
        self.block(p, 41, 87, 11, 2, PAPER, u)
        self.block(p, 43, 88, 6, 1, "#a99776", u)
        self.block(p, 52, 86, 5, 7, "#d8e0d1", u)
        self.block(p, 53, 84, 3, 2, "#d8e0d1", u)
        self.block(p, 56, 87, 2, 3, "#d8e0d1", u)

        # Raccoon character seated behind the desk.
        # Tail behind body.
        self.block(p, 21, 78, 9, 7, "#777f7a", u)
        self.block(p, 18, 76, 5, 5, "#353e3d", u)
        self.block(p, 18, 82, 6, 3, "#d3d0bd", u)
        # Ears and head.
        self.block(p, 34, 47, 8, 9, "#737c78", u)
        self.block(p, 59, 47, 8, 9, "#737c78", u)
        self.block(p, 36, 49, 4, 5, "#bd8d78", u)
        self.block(p, 61, 49, 4, 5, "#bd8d78", u)
        self.block(p, 35, 51, 31, 29, "#8d9690", u)
        self.block(p, 38, 48, 25, 6, "#8d9690", u)
        # Face mask.
        self.block(p, 36, 59, 30, 10, "#343d3d", u)
        self.block(p, 39, 59, 9, 7, "#222a2b", u)
        self.block(p, 54, 59, 9, 7, "#222a2b", u)
        # Eyes and muzzle.
        self.block(p, 42, 60, 3, 3, "#f3ead4", u)
        self.block(p, 56, 60, 3, 3, "#f3ead4", u)
        self.block(p, 43, 61, 2, 2, "#202323", u)
        self.block(p, 56, 61, 2, 2, "#202323", u)
        self.block(p, 46, 68, 11, 7, "#d7d2c0", u)
        self.block(p, 50, 67, 4, 3, "#292d2d", u)
        self.block(p, 48, 74, 7, 1, "#6b5148", u)
        # Suit shoulders and torso.
        self.block(p, 29, 79, 43, 17, "#263d37", u)
        self.block(p, 33, 76, 35, 7, "#263d37", u)
        self.block(p, 44, 78, 14, 17, "#e6ddc9", u)
        self.block(p, 49, 78, 5, 14, "#a94f43", u)
        self.block(p, 39, 81, 5, 13, "#d3d0bd", u)
        self.block(p, 58, 81, 5, 13, "#d3d0bd", u)
        self.block(p, 29, 91, 43, 4, "#1c302b", u)
        # Paws on desk.
        self.block(p, 35, 91, 9, 4, "#8d9690", u)
        self.block(p, 59, 91, 9, 4, "#8d9690", u)

        p.end()


class BulletinBoard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("corkBoard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 15, 17, 15)
        layout.setSpacing(9)

        header = QHBoxLayout()
        header.addWidget(ui_label("오늘의 국장", 15, PAPER_INK, True))
        header.addStretch()
        header.addWidget(ui_label("DAILY BRIEF", 8, "#8a6946", True))
        layout.addLayout(header)
        self.date = ui_label("최근 거래일 · 데이터 연결 대기", 8, "#806d52")
        layout.addWidget(self.date)

        indices = QHBoxLayout()
        indices.addWidget(self.index_card("KOSPI", "—", "등락률 대기"))
        indices.addWidget(self.index_card("KOSDAQ", "—", "등락률 대기"))
        layout.addLayout(indices)

        self.add_note(layout, "강세 업종  ▲", "업종별 상승률 상위 3~5개 표시 대기")
        self.add_note(layout, "약세 업종  ▼", "업종별 하락률 상위 3~5개 표시 대기")
        self.add_note(layout, "테마 & 수급", "오늘의 강세·약세 테마\n외국인 · 기관 · 개인 순매수")
        self.add_note(layout, "시장 한 줄 요약", "실제 시장 데이터가 연결되면 장세와 원인을 요약합니다.", True)
        layout.addStretch()
        note = ui_label("실제 데이터 연결 전 · 예시 수치 없음", 8, "#806d52")
        layout.addWidget(note)

    def index_card(self, title, value, note):
        f = QFrame()
        f.setStyleSheet("background:#f4ead1;border:1px solid #bda77e;border-radius:2px;")
        l = QVBoxLayout(f)
        l.setContentsMargins(8, 7, 8, 7)
        l.setSpacing(2)
        l.addWidget(ui_label(title, 8, "#846b4b", True))
        l.addWidget(ui_label(value, 19, PAPER_INK, True))
        l.addWidget(ui_label(note, 7, "#8c795c"))
        return f

    def add_note(self, layout, title, body, emphasis=False):
        pin = QHBoxLayout()
        pin.addWidget(ui_label("●", 8, RED, True))
        pin.addWidget(ui_label(title, 10, "#665139", True))
        pin.addStretch()
        layout.addLayout(pin)
        text = ui_label(body, 9, "#6f624e", emphasis)
        text.setWordWrap(True)
        text.setStyleSheet("background:#f1e6cc;padding:7px;border:1px solid #c6b38e;color:#6f624e;")
        layout.addWidget(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2 — The Korean Market Office")
        self.resize(1600, 960)
        self.setMinimumSize(1280, 820)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{BG}; color:{TEXT}; }}
            QFrame#card {{ background:{PANEL}; border:2px solid {BORDER}; border-radius:4px; }}
            QFrame#corkBoard {{ background:#bd9565; border:7px solid #65472f; border-radius:3px; }}
            QPushButton {{ background:#46534b;color:{TEXT};border:2px solid #697568;border-radius:3px;padding:8px 12px;font-weight:600; }}
            QPushButton:hover {{ border-color:{GOLD}; }}
            QLineEdit,QComboBox {{ background:#202a26;color:{TEXT};border:1px solid #68776b;border-radius:2px;padding:7px; }}
            QTabWidget::pane {{ border:2px solid #58665c;background:{PANEL_DARK}; }}
            QTabBar::tab {{ background:#39463f;color:{MUTED};padding:9px 15px;border:1px solid #59665b; }}
            QTabBar::tab:selected {{ background:#58664f;color:#f4d99a; }}
            QTableWidget {{ background:#26332e;color:{TEXT};gridline-color:#536056;border:0; }}
            QHeaderView::section {{ background:#46534b;color:#e4d8bd;border:0;padding:8px; }}
            QTextEdit {{ background:#202a26;color:{TEXT};border:1px solid #59665b;border-radius:2px;padding:7px; }}
        """)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.addWidget(ui_label("DONMULWON 2", 22, "#f0dfb9", True))
        brand.addWidget(ui_label("국내 주식 단기 스윙 분석실  ·  THE MARKET OFFICE", 9, MUTED))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(ui_label("KOSPI  ·  KOSDAQ", 10, GOLD, True))
        header.addWidget(ui_label("  ●  시세 연결 대기", 9, MUTED))
        outer.addLayout(header)

        # Small status plaques, not oversized generic dashboard cards.
        status = QHBoxLayout()
        for title, value, note in [
            ("KOSPI", "—", "최근 거래일"),
            ("KOSDAQ", "—", "최근 거래일"),
            ("시장 분위기", "분석 대기", "상승 / 하락 종목"),
            ("매수 신호", "0", "세 조건 동시 충족"),
        ]:
            plaque = make_card()
            plaque.setMaximumHeight(74)
            pl = QVBoxLayout(plaque)
            pl.setContentsMargins(12, 7, 12, 7)
            pl.setSpacing(1)
            pl.addWidget(ui_label(title, 8, MUTED, True))
            pl.addWidget(ui_label(value, 16, "#f1dfb7", True))
            pl.addWidget(ui_label(note, 7, MUTED))
            status.addWidget(plaque)
        outer.addLayout(status)

        workspace = QHBoxLayout()
        workspace.setSpacing(12)

        # Left wall: physical cork bulletin board.
        self.board = BulletinBoard()
        self.board.setMinimumWidth(265)
        self.board.setMaximumWidth(315)
        workspace.addWidget(self.board, 3)

        # Center: actual pixel-art office scene with raccoon at his own desk.
        scene_frame = make_card()
        scene_layout = QVBoxLayout(scene_frame)
        scene_layout.setContentsMargins(8, 8, 8, 8)
        scene_layout.setSpacing(5)
        scene_layout.addWidget(ui_label("ANALYST'S OFFICE", 9, GOLD, True))
        scene_layout.addWidget(PixelOfficeScene(), 1)
        scene_layout.addWidget(ui_label("월가의 너구리 애널리스트  ·  추세 전환 감시 중", 8, MUTED))
        workspace.addWidget(scene_frame, 4)

        # Right: monitor-like analysis workstation.
        monitor = make_card()
        monitor_layout = QVBoxLayout(monitor)
        monitor_layout.setContentsMargins(10, 10, 10, 10)
        monitor_layout.setSpacing(8)
        monitor_layout.addWidget(ui_label("TRADING TERMINAL", 10, GOLD, True))

        controls = QHBoxLayout()
        market = QComboBox()
        market.addItems(["전체 시장 · KOSPI + KOSDAQ", "KOSPI", "KOSDAQ"])
        kind = QComboBox()
        kind.addItems(["낙폭과대 + 테마주", "낙폭과대주", "테마주"])
        controls.addWidget(market, 2)
        controls.addWidget(kind, 1)
        monitor_layout.addLayout(controls)

        tabs = QTabWidget()
        screener = QWidget()
        sl = QVBoxLayout(screener)
        sl.setContentsMargins(8, 8, 8, 8)
        row = QHBoxLayout()
        row.addWidget(ui_label("발굴 종목", 11, TEXT, True))
        row.addStretch()
        search = QLineEdit()
        search.setPlaceholderText("종목명 / 코드")
        search.setMaximumWidth(180)
        row.addWidget(search)
        sl.addLayout(row)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["종목", "유형", "RSI", "MACD", "10일선", "상태"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setRowCount(1)
        for c, value in enumerate(["데이터 대기", "—", "미확인", "미확인", "미확인", "신호 없음"]):
            table.setItem(0, c, QTableWidgetItem(value))
        sl.addWidget(table)
        tabs.addTab(screener, "종목 발굴")

        report = QWidget()
        rl = QVBoxLayout(report)
        rl.setContentsMargins(8, 8, 8, 8)
        rl.addWidget(ui_label("애널리스트 분석 보고서", 11, TEXT, True))
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_text.setText(
            "아직 분석된 종목이 없습니다.\n\n"
            "실제 데이터 연결 후 표시할 항목\n"
            "• 기업 / 테마 설명과 52주 고점 대비 하락률\n"
            "• RSI(10/14), MACD(5/10/9), 10일선 신호\n"
            "• 매물대, 볼린저밴드, 거래량 및 거래대금\n"
            "• MACD 추세 전환 기준 익절·손절\n"
            "• 손익비, 보유 기간, 무효화 조건\n\n"
            "※ 현재 화면은 디자인 시제품이며 실제 시세가 아닙니다."
        )
        rl.addWidget(report_text)
        tabs.addTab(report, "분석 보고서")

        chart = QWidget()
        cl = QVBoxLayout(chart)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.addWidget(ui_label("차트 분석", 11, TEXT, True))
        chart_box = make_card()
        cbl = QVBoxLayout(chart_box)
        cbl.addStretch()
        cbl.addWidget(ui_label("차트 데이터 연결 대기", 15, MUTED, True), alignment=Qt.AlignmentFlag.AlignCenter)
        cbl.addWidget(ui_label("캔들 · 10일선 · 240일선 · 매물대 · 볼린저밴드", 8, MUTED), alignment=Qt.AlignmentFlag.AlignCenter)
        cbl.addWidget(ui_label("RSI · MACD · 거래량 패널", 8, MUTED), alignment=Qt.AlignmentFlag.AlignCenter)
        cbl.addStretch()
        cl.addWidget(chart_box)
        tabs.addTab(chart, "차트 분석")
        monitor_layout.addWidget(tabs, 1)
        workspace.addWidget(monitor, 5)

        outer.addLayout(workspace, 1)
        footer = QHBoxLayout()
        footer.addWidget(ui_label("DONMULWON 2  ·  PIXEL ART OFFICE UI", 8, MUTED))
        footer.addStretch()
        footer.addWidget(ui_label("자동매매 없음  ·  시장 데이터 연동 예정", 8, MUTED))
        outer.addLayout(footer)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
