"""Qt worker for running network-bound market analysis without freezing the GUI."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .analyzer import DonmulwonAnalyzer


class AnalysisWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, task: str, ticker: str = "", market: str = "KOSPI"):
        super().__init__()
        self.task = task
        self.ticker = ticker
        self.market = market
        self.analyzer = DonmulwonAnalyzer()

    @Slot()
    def run(self):
        try:
            if self.task == "ticker":
                result = self.analyzer.analyze_ticker(self.ticker)
            elif self.task == "bulletin":
                result = self.analyzer.market_bulletin(self.market)
            elif self.task == "scan":
                result = self.analyzer.scan_market(
                    self.market,
                    progress=lambda current, total, symbol: self.progress.emit(
                        current, total, symbol
                    ),
                )
            else:
                raise ValueError(f"지원하지 않는 분석 작업: {self.task}")

            if result.ok:
                self.finished.emit(result.data)
            else:
                self.failed.emit(result.message)
        except Exception as exc:
            self.failed.emit(str(exc))
