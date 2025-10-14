
import PySide6QtAds as QtAds
from br_sdk.events import shutdown_event_server
from br_sdk.parse_steps import steps_from_file
from core.event_bridge import EventBridge
from core.worker import Worker
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_sequence = None
        self.config_path = None
        self._thread = None
        self._worker = None
        self.running = False

        self.set_header()
        self.set_central_widget()
        self.set_footer()
        self.set_bridge()
    
    def set_header(self):
        ribbon = self.set_ribbon()
        self.set_toolbar(ribbon)
 
    def set_bridge(self):
        self.bridge = EventBridge()
        self.bridge.qt_log_msg.connect(lambda log_msg: self.log_widget.appendPlainText(log_msg))
        
    def set_toolbar(self, ribbon):
        toolbar = QToolBar("Ribbon", self)
        toolbar.setMovable(True)
        toolbar.setFloatable(False)
        toolbar.addWidget(ribbon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        toolbar.orientationChanged.connect(ribbon.setOrientation)

    def set_central_widget(self):
        self.set_dock_manager()
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

    def set_footer(self):
        dock = QDockWidget("Log", self)
        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    
    def set_ribbon(self):
        run_ribbon = RunSequenceRibbonPage()
        run_ribbon.sequence_selected.connect(self._sequence_selected)
        run_ribbon.start_btn.clicked.connect(self._start_sequence)

        config_ribbon = RibbonPage("Config", 3)

        instruments_ribbon = RibbonPage("Instruments", 8)
        instruments_ribbon.button_clicked.connect(self.handle_instrument_clicked)

        ribbon = TabbedRibbonContainer([run_ribbon, config_ribbon, instruments_ribbon])
        ribbon.tab_ribbon_index_changed.connect(self.change_page)
        return ribbon


    def set_dock_manager(self):
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.OpaqueSplitterResize, True)
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.XmlCompressionEnabled, False)
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.FocusHighlighting, True)
       

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
        for step in self.steps_data.steps:
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

        self.bridge.wait_until_ready(timeout=1.0)

        self._thread.started.connect(self._worker.run)
        self._thread.start()
        self.running = True

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self.bridge.shutdown()
        shutdown_event_server()
        super().closeEvent(event)
        event.accept()
