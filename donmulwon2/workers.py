"""Qt worker for network-bound analysis; keeps the interface responsive."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot
from pykrx import stock

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

    @Slot()
    def run(self):
        try:
            analyzer = DonmulwonAnalyzer()
            if self.task == "ticker":
                result = analyzer.analyze_ticker(self.ticker)
                self._emit_result(result)
            elif self.task == "bulletin":
                result = analyzer.market_bulletin(self.market)
                self._emit_result(result)
            elif self.task == "history":
                self.finished.emit(analyzer.store.recent_analyses(limit=50))
            elif self.task == "dashboard":
                markets = {}
                errors = []
                trading_date = analyzer.provider.latest_trading_date()
                for market, index_code in (("KOSPI", "1001"), ("KOSDAQ", "2001")):
                    bulletin = analyzer.market_bulletin(market, trading_date)
                    if bulletin.ok:
                        item = bulletin.data
                        index_result = analyzer.provider.index_history(index_code, days=10)
                        if index_result.ok and not index_result.data.empty:
                            last = index_result.data.iloc[-1]
                            item["index_close"] = _safe_float(last.get("종가"))
                            item["index_change"] = _safe_float(last.get("등락률"))
                        else:
                            item["index_close"] = None
                            item["index_change"] = None
                        markets[market] = item
                    else:
                        errors.append(f"{market}: {bulletin.message}")
                if not markets:
                    raise RuntimeError("시장 데이터를 모두 받지 못했습니다. " + " / ".join(errors))
                self.finished.emit({
                    "date": next(iter(markets.values())).get("date"),
                    "markets": markets,
                    "errors": errors,
                })
            elif self.task == "scan":
                result = analyzer.scan_market(
                    self.market,
                    progress=lambda current, total, symbol:
                        self.progress.emit(current, total, symbol),
                )
                self._emit_result(result)
            else:
                raise ValueError(f"지원하지 않는 분석 작업: {self.task}")
        except Exception as exc:
            self.failed.emit(str(exc))

    def _emit_result(self, result):
        if result.ok:
            self.finished.emit(result.data)
        else:
            self.failed.emit(result.message)


def _safe_float(value):
    try:
        value = float(value)
        return value if value == value else None
    except (TypeError, ValueError):
        return None
