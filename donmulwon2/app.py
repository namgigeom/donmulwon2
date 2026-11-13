import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QTabWidget, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QProgressBar
)

BG = "#171b1d"
PANEL = "#22292b"
PANEL2 = "#293234"
TEXT = "#e9e5dc"
MUTED = "#a6aaa3"
ACCENT = "#c6a36a"
GREEN = "#83b99a"
RED = "#cf8277"
BORDER = "#394345"

def label(text, size=10, color=TEXT, bold=False):
    w = QLabel(text)
    w.setFont(QFont("Malgun Gothic", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    w.setStyleSheet(f"color:{color};")
    return w

def panel():
    f = QFrame()
    f.setObjectName("panel")
    f.setFrameShape(QFrame.Shape.NoFrame)
    return f

def metric_card(title, value, note=""):
    f = panel()
    l = QVBoxLayout(f)
    l.setContentsMargins(14, 12, 14, 12)
    l.setSpacing(5)
    l.addWidget(label(title, 9, MUTED, True))
    l.addWidget(label(value, 17, TEXT, True))
    if note:
        l.addWidget(label(note, 9, MUTED))
    return f

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2 | Korean Swing Analyst")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{BG}; color:{TEXT}; }}
            QFrame#panel {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:10px; }}
            QPushButton {{
                background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:7px; padding:9px 14px; font-weight:600;
            }}
            QPushButton:hover {{ border:1px solid {ACCENT}; }}
            QPushButton#primary {{ background:{ACCENT}; color:#1d211f; border:0; }}
            QLineEdit, QComboBox {{
                background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER};
                border-radius:6px; padding:8px;
            }}
            QTabWidget::pane {{ border:1px solid {BORDER}; border-radius:8px; }}
            QTabBar::tab {{ background:{PANEL}; color:{MUTED}; padding:10px 18px; }}
            QTabBar::tab:selected {{ color:{ACCENT}; border-bottom:2px solid {ACCENT}; }}
            QTableWidget {{
                background:{PANEL}; color:{TEXT}; gridline-color:{BORDER};
                border:0; selection-background-color:{PANEL2};
            }}
            QHeaderView::section {{
                background:{PANEL2}; color:{MUTED}; border:0; padding:8px;
            }}
            QTextEdit {{ background:{PANEL2}; color:{TEXT}; border:1px solid {BORDER}; border-radius:7px; }}
            QProgressBar {{ background:{PANEL2}; border:0; border-radius:4px; height:7px; }}
            QProgressBar::chunk {{ background:{ACCENT}; border-radius:4px; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(14)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.addWidget(label("DONMULWON 2", 20, TEXT, True))
        brand.addWidget(label("ONE ANALYST. ONE MISSION. FIND THE NEXT TREND.", 9, MUTED))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(label("KOSPI  ·  KOSDAQ", 10, ACCENT, True))
        header.addWidget(label("  ●  데이터 미연결", 9, MUTED))
        outer.addLayout(header)

        # Market strip
        strip = QHBoxLayout()
        strip.addWidget(metric_card("KOSPI", "—", "시세 연결 대기"))
        strip.addWidget(metric_card("KOSDAQ", "—", "시세 연결 대기"))
        strip.addWidget(metric_card("시장 감시", "준비 중", "실제 스캔 엔진 미연결"))
        strip.addWidget(metric_card("매수 신호", "0", "실제 데이터 없음"))
        outer.addLayout(strip)

        body = QHBoxLayout()
        body.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(12)

        analyst = panel()
        al = QHBoxLayout(analyst)
        al.setContentsMargins(16, 14, 16, 14)
        avatar = QFrame()
        avatar.setFixedSize(92, 108)
        avatar.setStyleSheet(f"background:{PANEL2}; border:1px dashed {ACCENT}; border-radius:9px;")
        avl = QVBoxLayout(avatar)
        avl.addStretch()
        avl.addWidget(label("RACCOON", 10, ACCENT, True), alignment=Qt.AlignmentFlag.AlignCenter)
        avl.addWidget(label("캐릭터 원화 자리", 8, MUTED), alignment=Qt.AlignmentFlag.AlignCenter)
        avl.addStretch()
        al.addWidget(avatar)
        bio = QVBoxLayout()
        bio.addWidget(label("월가의 너구리 애널리스트", 15, TEXT, True))
        bio.addWidget(label("국내 주식 · 추세 전환 · 단기 스윙", 9, MUTED))
        bio.addStretch()
        bio.addWidget(label("“세 가지 신호가 모두 확인되기 전에는 매수 신호를 내지 않는다.”", 10, ACCENT))
        al.addLayout(bio, 1)
        left.addWidget(analyst)

        filters = panel()
        fl = QVBoxLayout(filters)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.addWidget(label("종목 발굴 조건", 13, TEXT, True))
        row = QHBoxLayout()
        row.addWidget(QComboBox())
        row.itemAt(0).widget().addItems(["전체 시장 · KOSPI + KOSDAQ", "KOSPI", "KOSDAQ"])
        row.addWidget(QComboBox())
        row.itemAt(1).widget().addItems(["낙폭과대 + 테마주", "낙폭과대주", "테마주"])
        fl.addLayout(row)
        fl.addWidget(label("필수 매수 신호", 10, MUTED, True))
        for name, desc in [
            ("RSI(10) / RSI(14)", "두 선 상향 교차 + 상승 방향"),
            ("MACD(5, 10, 9)", "MACD선·시그널선 상향 교차 + 상승 방향"),
            ("10일 이동평균선", "캔들의 아래→위 돌파"),
        ]:
            r = QHBoxLayout()
            r.addWidget(label("●", 10, ACCENT, True))
            r.addWidget(label(name, 10, TEXT, True))
            r.addStretch()
            r.addWidget(label(desc, 9, MUTED))
            fl.addLayout(r)
        fl.addWidget(label("보조 확인: 매물대 · 볼린저 밴드 · 거래량/거래대금 · 240일선 위험 표시", 9, MUTED))
        scan = QPushButton("시장 스캔 엔진 연결 대기")
        scan.setEnabled(False)
        fl.addWidget(scan)
        left.addWidget(filters)
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(12)
        tabs = QTabWidget()
        screener = QWidget()
        sl = QVBoxLayout(screener)
        sl.setContentsMargins(12, 12, 12, 12)
        top = QHBoxLayout()
        top.addWidget(label("발굴 종목", 13, TEXT, True))
        top.addStretch()
        search = QLineEdit()
        search.setPlaceholderText("종목명 또는 코드 검색")
        search.setMaximumWidth(240)
        top.addWidget(search)
        sl.addLayout(top)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["종목", "유형", "RSI 교차", "MACD 교차", "10일선 돌파", "상태"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setRowCount(1)
        values = ["실제 데이터 대기", "—", "미확인", "미확인", "미확인", "신호 없음"]
        for c, v in enumerate(values):
            table.setItem(0, c, QTableWidgetItem(v))
        sl.addWidget(table)
        tabs.addTab(screener, "종목 발굴")

        report = QWidget()
        rl = QVBoxLayout(report)
        rl.setContentsMargins(12, 12, 12, 12)
        rl.addWidget(label("너구리 애널리스트 보고서", 13, TEXT, True))
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_text.setText(
            "아직 분석된 종목이 없습니다.\\n\\n"
            "실제 시세·재무·수급 데이터 연결 후 다음 내용을 표시합니다.\\n"
            "• 종목 설명 및 상승 재료\\n"
            "• 고점 대비 하락률과 최근 저점\\n"
            "• RSI / MACD / 10일선 신호 발생 시각\\n"
            "• 위쪽 매물대와 볼린저 밴드 기준 잔여 상승 여력\\n"
            "• 진입 구간 / 1차·2차 익절 / 손절 / 예상 보유 기간\\n\\n"
            "※ 현재 화면은 GUI 시제품이며 실제 종목 추천이나 시세 데이터가 아닙니다."
        )
        rl.addWidget(report_text)
        tabs.addTab(report, "분석 보고서")

        chart = QWidget()
        cl = QVBoxLayout(chart)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.addWidget(label("차트 분석 영역", 13, TEXT, True))
        cl.addWidget(label("캔들 · 10일선 · 240일선 · 볼린저 밴드 · 매물대", 10, MUTED))
        placeholder = QFrame()
        placeholder.setMinimumHeight(250)
        placeholder.setStyleSheet(f"background:{PANEL2}; border:1px dashed {BORDER}; border-radius:8px;")
        pl = QVBoxLayout(placeholder)
        pl.addStretch()
        pl.addWidget(label("차트 데이터 연결 대기", 15, MUTED, True), alignment=Qt.AlignmentFlag.AlignCenter)
        pl.addWidget(label("RSI(10/14) · MACD(5/10/9) · 거래량 패널 포함 예정", 9, MUTED), alignment=Qt.AlignmentFlag.AlignCenter)
        pl.addStretch()
        cl.addWidget(placeholder)
        tabs.addTab(chart, "차트 분석")
        right.addWidget(tabs, 1)

        body.addLayout(left, 4)
        body.addLayout(right, 6)
        outer.addLayout(body, 1)

        footer = QHBoxLayout()
        footer.addWidget(label("DONMULWON 2  |  GUI PROTOTYPE", 8, MUTED))
        footer.addStretch()
        footer.addWidget(label("자동매매 없음 · 데이터 연결 전 시제품", 8, MUTED))
        outer.addLayout(footer)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
