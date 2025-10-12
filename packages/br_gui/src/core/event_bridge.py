from br_sdk.br_types import Step, StepResult
from br_sdk.events import EventSubscriber, ensure_event_server
from PySide6.QtCore import QObject, Signal


class EventBridge(QObject):
    qt_step_started = Signal(Step)
    qt_step_ended = Signal(StepResult)
    qt_log_msg = Signal(str)

    def __init__(self):
        super().__init__()
        server = ensure_event_server()
        self._subscriber = EventSubscriber(
            on_step_started=self.qt_step_started.emit,
            on_step_ended=self.qt_step_ended.emit,
            on_log=lambda msg, level: self.qt_log_msg.emit(msg),
            address=server.address,
        )
        self._subscriber.start()

    def shutdown(self):
        self._subscriber.stop()

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        return self._subscriber.wait_until_ready(timeout)
