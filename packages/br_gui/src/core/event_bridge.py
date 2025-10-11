from br_sdk.br_types import Step, StepResult
from br_sdk.events import log_msg, step_ended, step_started
from PySide6.QtCore import QObject, Signal


class EventBridge(QObject):
    qt_step_started = Signal(Step)
    qt_step_ended = Signal(StepResult)
    qt_log_msg = Signal(str)

    def __init__(self):
        super().__init__()

        step_started.connect(self.handle_step_started)
        step_ended.connect(self.handle_step_ended)
        log_msg.connect(self.handle_log_msg)
        
    def handle_step_started(self, sender, step):
        self.qt_step_started.emit(step)

    def handle_step_ended(self, sender, result):
        self.qt_step_ended.emit(result)

    def handle_log_msg(self, sender, log, record):
        self.qt_log_msg.emit(log)
