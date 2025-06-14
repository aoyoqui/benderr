from PySide6.QtCore import QObject, Signal

from br_tester.br_types import StepResult, Step
from br_tester.events import step_ended, step_started

class EventBridge(QObject):
    qt_step_started = Signal(Step)
    qt_step_ended = Signal(StepResult)

    def __init__(self):
        super().__init__()

        step_started.connect(self.handle_step_started)
        step_ended.connect(self.handle_step_ended)
        
    def handle_step_started(self, sender, step):
        self.qt_step_started.emit(step)

    def handle_step_ended(self, sender, result):
        self.qt_step_ended.emit(result)
