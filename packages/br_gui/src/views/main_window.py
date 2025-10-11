import sys
from importlib.metadata import entry_points
from pathlib import Path

import PySide6QtAds as QtAds
from br_tester.br_logging import setup_logger
from br_tester.config import AppConfig
from br_tester.parse_steps import steps_from_file
from core.event_bridge import EventBridge
from PySide6.QtCore import QObject, Qt, QThread, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QPlainTextEdit,
    QStackedWidget,
    QTableWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from views.ribbon import RibbonPage, RunSequenceRibbonPage, TabbedRibbonContainer
from views.step_widget import StepWidget


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

        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.OpaqueSplitterResize, True)
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.XmlCompressionEnabled, False)
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.FocusHighlighting, True)

        run_ribbon = RunSequenceRibbonPage()
        run_ribbon.sequence_selected.connect(self._sequence_selected)
        run_ribbon.start_btn.clicked.connect(self._start_sequence)
        config_ribbon = RibbonPage("Config", 3)
        instruments_ribbon = RibbonPage("Instruments", 8)
        instruments_ribbon.button_clicked.connect(self.handle_instrument_clicked)
        ribbon = TabbedRibbonContainer([run_ribbon, config_ribbon, instruments_ribbon])
        ribbon.tab_ribbon_index_changed.connect(self.change_page)

        toolbar = QToolBar("Ribbon", self)
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        toolbar.addWidget(ribbon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        toolbar.orientationChanged.connect(ribbon.setOrientation)

        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        run_widget = QWidget()
        self.run_layout = QVBoxLayout(run_widget)
        self.central_widget.addWidget(run_widget)

        config_widget = QWidget()
        self.central_widget.addWidget(config_widget)

        self.instruments_widget = QtAds.CDockManager(self.central_widget)
        text_edit = QPlainTextEdit()
        text_edit.setPlaceholderText("This is the central instruments widget. Can be removed if no default needed")
        central_instr_widget = QtAds.CDockWidget("CentralWidget")
        central_instr_widget.setWidget(text_edit)
        central_instr_area = self.instruments_widget.setCentralWidget(central_instr_widget)
        central_instr_area.setAllowedAreas(QtAds.DockWidgetArea.OuterDockAreas)
        self.central_widget.addWidget(self.instruments_widget)


        dock = QDockWidget("Log", self)
        log_widget = QPlainTextEdit()
        log_widget.setReadOnly(True)

        self.bridge = EventBridge()

        self.bridge.qt_log_msg.connect(lambda log_msg: log_widget.appendPlainText(log_msg))
        dock.setWidget(log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        
        self._thread: QThread | None = None
        self._worker: Worker | None = None
        self.running = False
        

    def handle_instrument_clicked(self, name):
        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(10)
        print(name)
        table_dock_widget = QtAds.CDockWidget(name)
        table_dock_widget.setWidget(table)
        table_dock_widget.setMinimumSizeHintMode(QtAds.CDockWidget.MinimumSizeHintFromDockWidget)
        table_dock_widget.resize(250, 150)
        table_dock_widget.setMinimumSize(200, 150)
        self.instruments_widget.addDockWidget(QtAds.DockWidgetArea.LeftDockWidgetArea, table_dock_widget)


    def change_page(self, index):
        self.central_widget.setCurrentIndex(index)

    def _sequence_selected(self, sequence_name, config_path):
        self.config_path = config_path
        self.steps_data = steps_from_file(self.config_path)
        self.selected_sequence = sequence_name
        for step in self.steps_data:
            step_widget = StepWidget(step, self.bridge)
            self.run_layout.addWidget(step_widget)
        self.run_layout.addStretch()

    def _start_sequence(self):
        if self.running:
            self._thread.quit()
            self._thread.wait()
            self.running = False
        self._thread = QThread()
        self.steps_data = steps_from_file(self.config_path)
        self._worker = Worker(self.selected_sequence, self.steps_data)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._thread.start()
        self.running = True

def main():
    AppConfig.load(profile="gui", config_dirs=["./config"])
    setup_logger()
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
