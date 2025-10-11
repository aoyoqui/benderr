# From https://github.com/EsoCoding/PySide6-Collapsible-Widget/blob/main/README.md

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QSpacerItem, QStackedLayout, QVBoxLayout, QWidget


class CollapsibleWidget(QWidget):
    def __init__(self, name, content_widget):
        super().__init__()
        self.content = content_widget
        self.expand_ico = ">"
        self.collapse_ico = "v"
        self.setSizePolicy(QSizePolicy.Expanding,
                           QSizePolicy.Fixed)

        stacked = QStackedLayout(self)
        stacked.setStackingMode(QStackedLayout.StackAll)

        self.background = QLabel()
        self.background.setStyleSheet(
            "QLabel{ background-color: rgb(93, 93, 93); padding-top: -20px; border-radius:2px}")

        widget = QWidget()
        layout = QHBoxLayout(widget)

        self.icon = QLabel()
        self.icon.setText(self.expand_ico)
        self.icon.setStyleSheet(
            "QLabel { font-weight: bold; font-size: 20px; color: #000000 }")
        layout.addWidget(self.icon)

        layout.addWidget(self.icon)
        layout.addWidget(self.icon)
        layout.setContentsMargins(11, 0, 11, 0)

        font = QFont()
        font.setBold(True)
        label = QLabel(name)
        label.setStyleSheet("QLabel { margin-top: 5px; }")
        label.setFont(font)

        layout.addWidget(label)
        layout.addItem(QSpacerItem(
            0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))

        stacked.addWidget(widget)
        stacked.addWidget(self.background)

        self.background.setMinimumHeight(layout.sizeHint().height() * 1.5)

    def mousePressEvent(self, *args):
        self.expand() if not self.content.isVisible() else self.collapse()

    def expand(self):
        self.content.setVisible(True)
        self.icon.setText(self.collapse_ico)

    def collapse(self):
        self.content.setVisible(False)
        self.icon.setText(self.expand_ico)


class Container(QWidget):
    def __init__(self, name, color_background=False):
            super(Container, self).__init__()
    
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
    
            self._content_widget = QWidget()
    
            if color_background:
                self._content_widget.setStyleSheet(".QWidget{background-color: rgb(73, 73, 73); "
                                                   "margin-left: 2px; padding-top: 20px; margin-right: 2px}")
   
            self.header = CollapsibleWidget(name, self._content_widget)
            layout.addWidget(self.header)
            layout.addWidget(self._content_widget)
    
            self.collapse = self.header.collapse
            self.expand = self.header.expand
            self.toggle = self.header.mousePressEvent
            self.header.collapse()
    
    @property
    def contentWidget(self):
            return self._content_widget
    