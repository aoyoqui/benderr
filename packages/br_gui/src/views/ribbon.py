
import sys
from pathlib import Path
from importlib.metadata import entry_points

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QToolBar,
    QWidget, QBoxLayout, QTabBar, QStackedWidget, QToolButton,
    QVBoxLayout, QComboBox, QPushButton, QFileDialog
)
from PySide6.QtCore import Qt, Signal

class RibbonButton(QToolButton):
    def __init__(self, text: str, icon=None):
        super().__init__()
        self.setText(text)
        if icon:
            self.setIcon(icon)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QToolButton { background-color: transparent; border: none;}
            QToolButton:hover { background-color: darkgray; }
            """
        )
        self.clicked.connect(lambda: print(f"I was clicked: {self.text()}"))

class RibbonPage(QWidget):
    def __init__(self, name: str, button_count: int = 4):
        super().__init__()
        self.name = name
        self._layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self._layout.setContentsMargins(5,5,5,5)
        self._layout.setSpacing(3)

        for i in range(1, button_count+1):
            btn = RibbonButton(f"{name} {i}")
            self._layout.addWidget(btn)
        self._layout.addStretch()

    def setOrientation(self, orientation: Qt.Orientation):
        if orientation == Qt.Vertical:
            self._layout.setDirection(QBoxLayout.TopToBottom)
        else:
            self._layout.setDirection(QBoxLayout.LeftToRight)

class LoadManualSeqWidget(QWidget):
    sequence_selected = Signal(str, str)
    DISPLAY_TEXT = "-Select Sequence-"
    def __init__(self):
        super().__init__()
        self.selected_sequence = None
        self.config_path: Path | None = None
        
        layout = QVBoxLayout()

        seq_dropdown = QComboBox()
        seq_dropdown.setMaximumWidth(150)
        seq_dropdown.addItem(self.DISPLAY_TEXT)
        for ep in entry_points(group="sequences"):
            seq_dropdown.addItem(ep.name)
        seq_dropdown.currentTextChanged.connect(self._update_sequence_name_selected)
        layout.addWidget(seq_dropdown)

        self.load_btn = QPushButton("Select Config")
        self.load_btn.clicked.connect(self._select_config)
        layout.addWidget(self.load_btn)
        self.setLayout(layout)
 
    def _select_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Step Config", filter="JSON Files (*.json)"
        )
        if not path:
            return
        
        self.config_path = str(Path(path))
        
        self._update_start_state()

    def _update_sequence_name_selected(self, txt):
        self.selected_sequence = (txt if txt not in ("", self.DISPLAY_TEXT) else None)
        self._update_start_state()

    def _update_start_state(self):
        self.sequence_selected.emit(self.selected_sequence, self.config_path)


class RunSequenceRibbonPage(QWidget):
    sequence_selected = Signal(str, str)
    def __init__(self):
        super().__init__()
        self.name = "Run"
        self._layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(3)

        load_sequence = LoadManualSeqWidget()
        load_sequence.sequence_selected.connect(self.handle_sequence_selected)
        self._layout.addWidget(load_sequence)

        self.start_btn = RibbonButton("Start Sequence")
        self.start_btn.setEnabled(False)
        self._layout.addWidget(self.start_btn)
        self._layout.addStretch()

    def handle_sequence_selected(self, sequence_name, config_path):
        print(f"Sequence was selected and received in {self.__class__.__name__}: {sequence_name}, {config_path}")
        self.sequence_name = sequence_name
        self.config_path = config_path
        enable = (bool(self.sequence_name and self.config_path))
        self.start_btn.setEnabled(enable)
        if enable:
            self.sequence_selected.emit(sequence_name, config_path)
 
    def setOrientation(self, orientation: Qt.Orientation):
        if orientation == Qt.Vertical:
            self._layout.setDirection(QBoxLayout.TopToBottom)
        else:
            self._layout.setDirection(QBoxLayout.LeftToRight)

           

class TabbedRibbonContainer(QWidget):
    def __init__(self, ribbon_pages):
        super().__init__()

        self._layout = QBoxLayout(QBoxLayout.TopToBottom)
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(0)
        self.setLayout(self._layout)

        self._tabbar = QTabBar()
        self._tabbar.setExpanding(False)
        self._tabbar.setStyleSheet("QTabBar { font-size: 14pt; }")
        self._stack  = QStackedWidget()
        self._pages  = []

        for page in ribbon_pages:
            self._tabbar.addTab("    "+page.name+"     ")
            self._stack.addWidget(page)
            self._pages.append(page)

        self._tabbar.currentChanged.connect(self._stack.setCurrentIndex)
        self._tabbar.setCurrentIndex(0)

        self._layout.addWidget(self._tabbar)
        self._layout.addWidget(self._stack)

    def setOrientation(self, orientation: Qt.Orientation):
        # Change the tab shape
        if orientation == Qt.Vertical:
            self._tabbar.setShape(QTabBar.RoundedWest)
        else:
            self._tabbar.setShape(QTabBar.RoundedNorth)

        # Clear out the layout’s contents **without throwing away the layout object**
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        # Flip direction on the existing layout
        if orientation == Qt.Vertical:
            self._layout.setDirection(QBoxLayout.LeftToRight)
        else:
            self._layout.setDirection(QBoxLayout.TopToBottom)

        # Re-add the widgets in the new order
        self._layout.addWidget(self._tabbar)
        self._layout.addWidget(self._stack)

        # Tell each page to flip its button‐flow
        for page in self._pages:
            page.setOrientation(orientation)
