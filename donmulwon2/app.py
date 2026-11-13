import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget, QVBoxLayout


class MainScreen(QWidget):
    """Show the approved DONMULWON 2 pixel-art screen as-is."""
    def __init__(self, image_path: Path):
        super().__init__()
        self.image = QPixmap(str(image_path))
        if self.image.isNull():
            raise RuntimeError(f"메인 화면 이미지를 읽을 수 없습니다: {image_path}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        # Keep the original artwork's aspect ratio and fill the window.
        scaled = self.image.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.drawPixmap(x, y, scaled)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DONMULWON 2")
        self.setMinimumSize(1000, 563)

        project_root = Path(__file__).resolve().parent
        image_path = project_root / "assets" / "donmulwon2_main_screen.png"

        if not image_path.exists():
            central = QWidget()
            layout = QVBoxLayout(central)
            message = QLabel(
                "메인 화면 이미지 파일을 찾을 수 없습니다.\n\n"
                "donmulwon2/assets/donmulwon2_main_screen.png\n"
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
