from PySide6.QtWidgets import QWidget, QTableView, QVBoxLayout, QHeaderView, QSizePolicy
from PySide6.QtCore import QModelIndex, QAbstractItemModel



class TableWidget(QWidget):
    def __init__(self, table_model: QAbstractItemModel):
        super().__init__()
        self.table_widget = QTableView()
        self.table_widget.setModel(table_model)
        parent_index = QModelIndex()
        self.row_count = table_model.rowCount(parent_index)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.set_height()
        layout = QVBoxLayout()
        layout.addWidget(self.table_widget)
        self.setLayout(layout)

    def set_height(self):
        header_h = self.table_widget.horizontalHeader().height()
        rows_h   = sum(self.table_widget.rowHeight(r) for r in range(self.row_count))
        frame    = 2 * self.table_widget.frameWidth()
        self.table_widget.setFixedHeight(header_h + rows_h + frame)
