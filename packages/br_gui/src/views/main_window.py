import sys
from importlib.metadata import entry_points
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QToolBar
from PySide6.QtCore import QThread, Slot, QObject, Qt
from views.step_widget import StepWidget
from views.ribbon import TabbedRibbonContainer, RunSequenceRibbonPage, RibbonPage
from core.event_bridge import EventBridge
from br_tester.parse_steps import steps_from_file
from br_tester.config import AppConfig


class Worker(QObject):
    def __init__(self, sequence, steps):
        super().__init__()
        self.selected_sequence = sequence
        self.steps = steps

    @Slot()
    def run(self):
        SequenceClass = get_sequence(self.selected_sequence)
        sequence = SequenceClass(self.steps)
        sequence.run()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_sequence = None
        self.config_path: Path | None = None

        run_ribbon = RunSequenceRibbonPage()
        run_ribbon.sequence_selected.connect(self._sequence_selected)
        run_ribbon.start_btn.clicked.connect(self._start_sequence)
        config_ribbon = RibbonPage("Config", 3)
        instruments_ribbon = RibbonPage("Instruments", 8)
        ribbon = TabbedRibbonContainer([run_ribbon, config_ribbon, instruments_ribbon])

        toolbar = QToolBar("Ribbon", self)
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        toolbar.addWidget(ribbon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        toolbar.orientationChanged.connect(ribbon.setOrientation)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.setLayout(self.main_layout)

        self.bridge = EventBridge()

        self._thread: QThread | None = None
        self._worker: Worker | None = None
        
    def _sequence_selected(self, sequence_name, config_path):
        self.steps_data = steps_from_file(config_path)
        self.selected_sequence = sequence_name
        for step in self.steps_data:
            step_widget = StepWidget(step, self.bridge)
            self.main_layout.addWidget(step_widget)
        self.main_layout.addStretch()

    def _start_sequence(self):
        self._thread = QThread()
        self._worker = Worker(self.selected_sequence, self.steps_data)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._thread.start()

def main():
    AppConfig.load(profile="gui", config_dirs=["./config"])
    
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized()
    sys.exit(app.exec())

def get_sequence(name: str):
    eps = entry_points(group="sequences")
    matches = {ep.name: ep.load() for ep in eps}
    if name not in matches:
        raise ValueError(f"Sequence '{name}' not found. Available: {list(matches)}")
    return matches[name]
