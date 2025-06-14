import sys
from importlib.metadata import entry_points
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QWidget, QComboBox, QFileDialog, QVBoxLayout, QApplication, QHBoxLayout, QPushButton
from PySide6.QtCore import QThread, Slot, QObject
from views.step_widget import StepWidget
from core.event_bridge import EventBridge
from br_tester.configurator import steps_from_file


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

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        header_layout = QHBoxLayout()        
        self.seq_dropdown = QComboBox()
        self.seq_dropdown.addItem("--- select sequence ---")
        for ep in entry_points(group="sequences"):
            self.seq_dropdown.addItem(ep.name)
        self.seq_dropdown.currentTextChanged.connect(self._update_start_state)
        header_layout.addWidget(self.seq_dropdown)

        self.load_btn = QPushButton("Select Config…")
        self.load_btn.clicked.connect(self._select_config)
        header_layout.addWidget(self.load_btn)

        self.start_btn = QPushButton("Start Sequence")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_sequence)
        header_layout.addWidget(self.start_btn)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.addLayout(header_layout)
        self.steps_layout = QVBoxLayout()
        self.main_layout.addLayout(self.steps_layout)
        self.setLayout(self.main_layout)

        self.bridge = EventBridge()

        self._thread: QThread | None = None
        self._worker: Worker | None = None
        

    def _start_sequence(self):
        self._thread = QThread()
        self._worker = Worker(self.selected_sequence, self.steps_data)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def _select_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Step Config", filter="JSON Files (*.json)"
        )
        if not path:
            return
        self.config_path = Path(path)
        self.steps_data = steps_from_file(self.config_path)
        
        self._populate_steps()
        self._update_start_state()

    def _update_start_state(self, txt=None):
        if self.selected_sequence is None:
            self.selected_sequence = (
                txt if txt not in ("", "--- select sequence ---") else None
            )
        self.start_btn.setEnabled(bool(self.selected_sequence and self.config_path))

    def _populate_steps(self):
        self.steps = []
        for step in self.steps_data:
            step_widget = StepWidget(step, self.bridge)
            self.main_layout.addWidget(step_widget)
            self.steps.append(step_widget)
        self.main_layout.addStretch()

def main():
    
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
