"""
Background worker for scanning missing media, so Nuke's UI does not freeze on big drives.

The scan runs in QThreadPool. Progress and the final plan are sent back through
Qt signals; the UI thread receives them as queued calls.
"""
from data import _media

try:
    from PySide2.QtCore import QObject, Signal, QRunnable, QThreadPool
except ModuleNotFoundError:
    from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool


class ReconnectSignals(QObject):
    """Signals emitted by ReconnectWorker."""
    progress = Signal(str)
    done = Signal(dict)


class ReconnectWorker(QRunnable):
    """Runs DataJson planning for one search folder, in a worker thread."""

    def __init__(self, data, search_root: str):
        super().__init__()
        self.setAutoDelete(False)
        self.signals = ReconnectSignals()
        self._data = data
        self._search_root = search_root
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the scan to stop at the next folder or item."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        """Plan the reconnect and report the result."""
        try:
            plan = self._data.plan_reconnect(self._search_root,
                                             cancelled=self.is_cancelled,
                                             progress=self.signals.progress.emit)
        except _media.ReconnectCancelled:
            plan = {'changes': [], 'stats': {}, 'search_root': self._search_root}
            plan['cancelled'] = True
        except Exception as error:  # report any failure to the UI instead of crashing the thread
            plan = {'changes': [], 'stats': {}, 'search_root': self._search_root, 'error': str(error)}

        plan.setdefault('cancelled', False)
        self.signals.done.emit(plan)


def start_scan(data, search_root: str, on_progress, on_done) -> ReconnectWorker:
    """
    Start a scan in the thread pool.

    :param data: tool_data.Data instance.
    :param search_root: Folder to search.
    :param on_progress: Slot receiving status text (called in the UI thread).
    :param on_done: Slot receiving the plan dict (called in the UI thread).
    :return: The worker. Keep a reference to it so it can be cancelled.
    """
    worker = ReconnectWorker(data, search_root)
    worker.signals.progress.connect(on_progress)
    worker.signals.done.connect(on_done)
    QThreadPool.globalInstance().start(worker)
    return worker
