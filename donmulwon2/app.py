import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QTabWidget, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QSizePolicy
)

# DONMULWON 2 - warm pixel-art trading office prototype
BG = "#252b29"
WALL = "#343b35"
WOOD = "#79583e"
WOOD_DARK = "#4d392c"
PAPER = "#e8dfc8"
PAPER_DARK = "#d5c8a8"
PANEL = "#303936"
PANEL2 = "#3b4540"
TEXT = "#f2ead8"
MUTED = "#b9b5a4"
GOLD = "#d6ad68"
GREEN = "#83b99a"
RED = "#d78578"
BORDER = "#5b6256"


def make_label(text, size=10, color=TEXT, bold=False):
    w = QLabel(text)
    w.setFont(QFont("Malgun Gothic", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    w.setStyleSheet(f"color:{color};")
    return w


def make_panel(title=None, paper=False):
    f = QFrame()
    f.setObjectName("paperPanel" if paper else "panel")
    f.setFrameShape(QFrame.Shape.NoFrame)
    if title:
        f.setProperty("panelTitle", title)
    return f


def section_title(text, color=TEXT):
    return make_label(text, 12, color, True)


class PixelRaccoon(QWidget):
    """Small hand-drawn pixel-art raccoon sprite, rendered natively in Qt."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(190, 210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        cell = max(4, min(self.width() // 28, self.height() // 30))
        ox = (self.width() - cell * 28) // 2
        oy = (self.height() - cell * 30) // 2
        colors = {
            " ": None, "F": "#8b9290", "D": "#454d4d", "L": "#c7c6b8",
            "B": "#252a2a", "W": "#f2ead8", "G": "#d6ad68", "S": "#263a35",
            "R": "#9b6557"
        }
        # 28 x 30 sprite. Suit, tie, ears, mask and muzzle.
        rows = [
            "       FFFFF        FFFFF       ",
            "      FFFFFF        FFFFFF      ",
            "     FFFFFFFF      FFFFFFFF     ",
            "    FFFFFFFFFF    FFFFFFFFFF    ",
            "   FFFFFFFFFFFFFFFFFFFFFFFFFF   ",
            "   FFFFFFFFFFFFFFFFFFFFFFFFFF   ",
            "  FFFFFFFFFFFFFFFFFFFFFFFFFFFF  ",
            "  FFFFFFFFFFFFFFFFFFFFFFFFFFFF  ",
            "  FFFDDDDFFFFFFFFFFFFFDDDDFFFF  ",
            "  FFDDWWDFFFFFFFFFFFFF DWWDDFF  ",
            "  FFDDWWDFFFFFFFFFFFFF DWWDDFF  ",
            "  FFFDDDDFFFFFFFFFFFFFDDDDFFFF  ",
            "  FFFFFFFFFFFFFFFFFFFFFFFFFFFF  ",
            "   FFFFFFFFLLLBBLLLFFFFFFFFFF    ",
            "    FFFFFFFLLLLLLLLFFFFFFFF      ",
            "      FFFFFFLLLLLLFFFFFF         ",
            "         FFFFFFFFFF              ",
            "       SSSSSSSSSSSSSSSS          ",
            "      SSSSSSSSSSSSSSSSSS         ",
            "      SSSSSSSSSRSSSSSSSSS         ",
            "      SSSSSSSSSRSSSSSSSSS         ",
            "      SSSSSSSSSRSSSSSSSSS         ",
            "     SSSSSSSSSSSSSSSSSSSSS        ",
            "     SSSSSSSSSSSSSSSSSSSSS        ",
            "    SSSSSSSSSSSSSSSSSSSSSSS       ",
            "    SSSSSSSSSSSSSSSSSSSSSSS       ",
            "    SSSSSSSSSSSSSSSSSSSSSSS       ",
            "   SSSSSSSSSSSSSSSSSSSSSSSSS      ",
            "   SSSSSSSSSSSSSSSSSSSSSSSSS      ",
            "   SSSSSSSSSSSSSSSSSSSSSSSSS      ",
        ]
        # Normalize to 28 columns and draw blocky pixels.
        for y, row in enumerate(rows):
            row = row[:28].ljust(28)
            for x, ch in enumerate(row):
                color = colors.get(ch)
                if color:
                    p.fillRect(ox + x * cell, oy + y * cell, cell, cell, QColor(color))
        # Suit lapels and shirt details.
        p.fillRect(ox + 12 * cell, oy + 18 * cell, 4 * cell, 8 * cell, QColor("#eee5d1"))
        p.fillRect(ox + 13 * cell, oy + 18 * cell, 2 * cell, 7 * cell, QColor("#a95749"))
        p.fillRect(ox + 10 * cell, oy + 19 * cell, 2 * cell, 6 * cell, QColor("#d0d0c0"))
        p.fillRect(ox + 16 * cell, oy + 19 * cell, 2 * cell, 6 * cell, QColor("#d0d0c0"))
        p.end()


class BulletinBoard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("bulletin")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        head.addWidget(make_label("TODAY'S MARKET", 13, "#4c3a2b", True))
        head.addStretch()
        head.addWidget(make_label("DAILY BRIEFING", 8, "#806448", True))
        layout.addLayout(head)
        self.date_label = make_label("최근 거래일 기준 · 데이터 연결 대기", 8, "#806448")
        layout.addWidget(self.date_label)

        index_grid = QGridLayout()
        index_grid.setSpacing(8)
        self.kospi_value = self.paper_metric("KOSPI", "—", "지수 데이터 대기")
        self.kosdaq_value = self.paper_metric("KOSDAQ", "—", "지수 데이터 대기")
        index_grid.addWidget(self.kospi_value, 0, 0)
        index_grid.addWidget(self.kosdaq_value, 0, 1)
        layout.addLayout(index_grid)

        layout.addWidget(self.paper_heading("▲ TODAY'S LEADERS"))
        self.leaders = self.paper_text("강세 업종 데이터 연결 대기\n업종별 등락률 상위 3~5개 표시")
        layout.addWidget(self.leaders)
        layout.addWidget(self.paper_heading("▼ TODAY'S LAGGARDS"))
        self.laggards = self.paper_text("약세 업종 데이터 연결 대기\n하락률 상위 3~5개 표시")
        layout.addWidget(self.laggards)
        layout.addWidget(self.paper_heading("FLOW & THEMES"))
        self.flow = self.paper_text("외국인 · 기관 · 개인 수급 대기\n거래대금 집중 테마 대기")
        layout.addWidget(self.flow)
        layout.addWidget(self.paper_heading("MARKET IN ONE SENTENCE"))
        self.summary = self.paper_text("시장 데이터가 연결되면 오늘의 장세를 한 문장으로 요약합니다.", True)
        layout.addWidget(self.summary)
        layout.addStretch()
        foot = make_label("※ 현재는 화면 시제품이며 실제 시세·수급 데이터가 아닙니다.", 8, "#806448")
        foot.setWordWrap(True)
        layout.addWidget(foot)

    def paper_metric(self, title, value, note):
        f = QFrame()
        f.setStyleSheet("background:#f0e7d2;border:1px solid #c7b895;border-radius:4px;")
        l = QVBoxLayout(f)
        l.setContentsMargins(9, 7, 9, 7)
        l.setSpacing(2)
        l.addWidget(make_label(title, 8, "#806448", True))
        l.addWidget(make_label(value, 18, "#51402f", True))
        l.addWidget(make_label(note, 7, "#927d61"))
        return f

    def paper_heading(self, text):
        return make_label(text, 9, "#6f5238", True)

    def paper_text(self, text, highlight=False):
        w = make_label(text, 9, "#4f493d" if highlight else "#756b58", highlight)
        w.setWordWrap(True)
        w.setStyleSheet("padding:2px 0;color:" + ("#4f493d" if highlight else "#756b58") + ";")
        return w


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2 | Korean Swing Analyst")
        self.resize(1580, 960)
        self.setMinimumSize(1250, 800)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{BG}; color:{TEXT}; }}
            QFrame#panel {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:7px; }}
            QFrame#bulletin {{ background:#b58b5e; border:4px solid #5a402d; border-radius:3px; }}
            QPushButton {{
                background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:4px; padding:8px 12px; font-weight:600;
            }}
            QPushButton:hover {{ border:1px solid {GOLD}; }}
            QPushButton#primary {{ background:{GOLD}; color:#29251e; border:0; }}
            QLineEdit, QComboBox {{
                background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:4px; padding:7px;
            }}
            QTabWidget::pane {{ border:1px solid {BORDER}; border-radius:5px; }}
            QTabBar::tab {{ background:{PANEL}; color:{MUTED}; padding:9px 14px; }}
            QTabBar::tab:selected {{ color:{GOLD}; border-bottom:2px solid {GOLD}; }}
            QTableWidget {{ background:{PANEL}; color:{TEXT}; gridline-color:{BORDER}; border:0; }}
            QHeaderView::section {{ background:{PANEL2}; color:{MUTED}; border:0; padding:8px; }}
            QTextEdit {{ background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER}; border-radius:4px; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(12)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.addWidget(make_label("DONMULWON 2", 21, TEXT, True))
        brand.addWidget(make_label("THE DAILY MARKET ROOM  ·  KOREAN EQUITY SWING DESK", 8, MUTED, True))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(make_label("KOSPI  /  KOSDAQ", 10, GOLD, True))
        header.addWidget(make_label("  ●  시세 데이터 연결 대기", 9, MUTED))
        outer.addLayout(header)

        strip = QHBoxLayout()
        for title, value, note in [
            ("KOSPI", "—", "최근 거래일 등락률"),
            ("KOSDAQ", "—", "최근 거래일 등락률"),
            ("시장 분위기", "분석 대기", "상승·하락 종목 비율"),
            ("매수 신호", "0", "세 조건 동시 충족"),
        ]:
            f = make_panel()
            l = QVBoxLayout(f)
            l.setContentsMargins(12, 8, 12, 8)
            l.addWidget(make_label(title, 8, MUTED, True))
            l.addWidget(make_label(value, 17, TEXT, True))
            l.addWidget(make_label(note, 8, MUTED))
            strip.addWidget(f)
        outer.addLayout(strip)

        content = QHBoxLayout()
        content.setSpacing(12)

        # Left: daily market bulletin board.
        self.board = BulletinBoard()
        self.board.setMinimumWidth(280)
        self.board.setMaximumWidth(340)
        content.addWidget(self.board, 3)

        # Center: analyst character and strategy.
        center_col = QVBoxLayout()
        center_col.setSpacing(10)
        character = make_panel()
        char_layout = QVBoxLayout(character)
        char_layout.setContentsMargins(12, 12, 12, 12)
        char_layout.addWidget(section_title("THE ANALYST"))
        char_layout.addWidget(make_label("월가의 너구리 애널리스트", 12, GOLD, True))
        char_layout.addWidget(make_label("국내 주식 · 추세 전환 · 단기 스윙", 8, MUTED))
        self.raccoon = PixelRaccoon()
        char_layout.addWidget(self.raccoon, 1)
        char_layout.addWidget(make_label("“세 가지 신호가 모두 확인되기 전에는 매수하지 않는다.”", 9, GOLD))
        center_col.addWidget(character, 5)

        rules = make_panel()
        rl = QVBoxLayout(rules)
        rl.setContentsMargins(13, 12, 13, 12)
        rl.addWidget(section_title("매수 필수 조건"))
        for name, desc in [
            ("01  RSI(10) / RSI(14)", "두 선 상향 교차 + 동반 상승"),
            ("02  MACD(5, 10, 9)", "MACD선이 시그널선 상향 돌파"),
            ("03  10일 이동평균선", "캔들이 아래에서 위로 돌파"),
        ]:
            item = QFrame()
            item.setStyleSheet(f"background:{PANEL2};border:1px solid {BORDER};border-radius:4px;")
            il = QVBoxLayout(item)
            il.setContentsMargins(9, 7, 9, 7)
            il.setSpacing(2)
            il.addWidget(make_label(name, 9, GOLD, True))
            il.addWidget(make_label(desc, 8, MUTED))
            rl.addWidget(item)
        rl.addWidget(make_label("보조 분석: 매물대 · 볼린저밴드 · 거래량 · 거래대금 · 240일선 위험", 8, MUTED))
        center_col.addWidget(rules, 3)
        content.addLayout(center_col, 3)

        # Right: scanner, chart and report.
        right = QVBoxLayout()
        right.setSpacing(9)
        controls = make_panel()
        ctl = QHBoxLayout(controls)
        ctl.setContentsMargins(10, 8, 10, 8)
        ctl.addWidget(section_title("MARKET SCANNER"))
        market = QComboBox()
        market.addItems(["전체 시장 · KOSPI + KOSDAQ", "KOSPI", "KOSDAQ"])
        ctl.addWidget(market)
        kind = QComboBox()
        kind.addItems(["낙폭과대 + 테마주", "낙폭과대주", "테마주"])
        ctl.addWidget(kind)
        scan = QPushButton("스캔 엔진 연결 대기")
        scan.setEnabled(False)
        ctl.addWidget(scan)
        right.addWidget(controls)

        tabs = QTabWidget()
        screener = QWidget()
        sl = QVBoxLayout(screener)
        sl.setContentsMargins(10, 10, 10, 10)
        top = QHBoxLayout()
        top.addWidget(section_title("발굴 종목"))
        top.addStretch()
        search = QLineEdit()
        search.setPlaceholderText("종목명 또는 코드 검색")
        search.setMaximumWidth(220)
        top.addWidget(search)
        sl.addLayout(top)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["종목", "유형", "RSI", "MACD", "10일선", "상태"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setRowCount(1)
        for c, value in enumerate(["실제 데이터 대기", "—", "미확인", "미확인", "미확인", "신호 없음"]):
            table.setItem(0, c, QTableWidgetItem(value))
        sl.addWidget(table)
        tabs.addTab(screener, "종목 발굴")

        report = QWidget()
        report_layout = QVBoxLayout(report)
        report_layout.setContentsMargins(10, 10, 10, 10)
        report_layout.addWidget(section_title("애널리스트 분석 보고서"))
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_text.setText(
            "아직 분석된 종목이 없습니다.\n\n"
            "실제 시세 데이터 연결 후 다음 항목을 표시합니다.\n"
            "• 기업 및 테마 설명 / 52주 고점 대비 하락률\n"
            "• RSI·MACD·10일선 신호와 발생 시각\n"
            "• 매물대·볼린저밴드·거래량 분석\n"
            "• 진입 구간 / MACD 추세 전환 기반 익절·손절\n"
            "• 손익비 / 예상 보유 기간 / 무효화 조건\n\n"
            "※ 현재 화면은 GUI 시제품이며 실제 투자 데이터가 아닙니다."
        )
        report_layout.addWidget(report_text)
        tabs.addTab(report, "분석 보고서")

        chart = QWidget()
        chart_layout = QVBoxLayout(chart)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        chart_layout.addWidget(section_title("차트 분석"))
        chart_placeholder = make_panel()
        cpl = QVBoxLayout(chart_placeholder)
        cpl.addStretch()
        cpl.addWidget(make_label("차트 데이터 연결 대기", 15, MUTED, True), alignment=Qt.AlignmentFlag.AlignCenter)
        cpl.addWidget(make_label("캔들 · 10일선 · 240일선 · 매물대 · 볼린저밴드", 9, MUTED), alignment=Qt.AlignmentFlag.AlignCenter)
        cpl.addWidget(make_label("RSI(10/14) · MACD(5/10/9) · 거래량 패널", 8, MUTED), alignment=Qt.AlignmentFlag.AlignCenter)
        cpl.addStretch()
        chart_layout.addWidget(chart_placeholder)
        tabs.addTab(chart, "차트 분석")
        right.addWidget(tabs, 1)
        content.addLayout(right, 5)

        outer.addLayout(content, 1)
        footer = QHBoxLayout()
        footer.addWidget(make_label("DONMULWON 2  |  PIXEL OFFICE UI PROTOTYPE", 8, MUTED))
        footer.addStretch()
        footer.addWidget(make_label("자동매매 없음  ·  실제 데이터 연결 전", 8, MUTED))
        outer.addLayout(footer)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
