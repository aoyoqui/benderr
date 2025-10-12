from br_sdk.br_types import Step, StepResult, Verdict
from core.event_bridge import EventBridge
from models.table_model import StepTableModel
from PySide6.QtWidgets import QVBoxLayout, QWidget

from views.collapsible_widget import Container
from views.table_widget import TableWidget


class StepWidget(QWidget):
    def __init__(self, step: Step, bridge: EventBridge):
        super().__init__()
        self.id = step.id
        self.bridge = bridge
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.container = Container(step.name, color_background=False)
        layout.addWidget(self.container)

        self.bridge.qt_step_ended.connect(self.handle_step_ended)
        self.bridge.qt_step_started.connect(self.handle_step_started)
        content_layout = QVBoxLayout(self.container.contentWidget)
        
        table = self._specs_table(step)
        content_layout.addWidget(table)
        self.setLayout(layout)
        
    def _specs_table(self, step: Step):
        if len(step.specs) > 0:
            table_model = StepTableModel(step, self.bridge)
            self.bridge.qt_step_ended.connect(table_model.handle_step_ended)
            table_widget = TableWidget(table_model)
            return table_widget
        return QWidget()

    def handle_step_started(self, step: Step):
        if self.id == step.id:
            print(f"Step widget received start {step}")
            self.container.header.background.setStyleSheet("QLabel { background-color: lightblue; }")

    def handle_step_ended(self, result: StepResult):
        if self.id == result.id:
            match result.verdict:
                case Verdict.PASSED: 
                    self.container.header.background.setStyleSheet("QLabel { background-color: green; }")
                case Verdict.FAILED: 
                    self.container.header.background.setStyleSheet("QLabel { background-color: red; }")
                case Verdict.ABORTED: 
                    self.container.header.background.setStyleSheet("QLabel { background-color: orange; }")
