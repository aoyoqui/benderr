from br_tester.br_types import StepResult, Step
from PySide6.QtCore import QAbstractTableModel, Qt
from core.event_bridge import EventBridge

class StepTableModel(QAbstractTableModel):
    def __init__(self, step: Step, bridge: EventBridge):
        super().__init__()
        self.id = step.id
        self.bridge = bridge
        self._headers = ["Passed", "Spec name", "Value", "Comparator", "Lower", "Upper", "Units"]
        self._data = [[None] * 7]*len(step.specs) 
        self.bridge.qt_step_ended.connect(self.handle_step_ended)
        for i, spec in enumerate(step.specs):
            self._data[i][1] = spec.name
            match spec.type.value:
                case "boolean":
                    self._data[i][3] = spec.pass_if_true
                case "numeric":
                    self._data[i][3] = spec.comparator
                    self._data[i][4] = spec.lower
                    self._data[i][5] = spec.upper
                    self._data[i][6] = spec.units


    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        return len(self._data)
    
    def columnCount(self, index):
        return len(self._data[0])

    def headerData(self, section, orientation, /, role = ...):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        else:
            return str(section + 1)

    def handle_step_ended(self, result: StepResult):
        if result.id == self.id:
            for i, res in enumerate(result.results):
                passed = "✅" if res.passed else "❌"
                self._data[i][0] = passed
                self._data[i][1] = res.spec.name
                match res.spec.type.value:
                    case "boolean":
                        self._data[i][2] = res.value
                    case "numeric":
                        self._data[i][2] = res.value

        top_left     = self.index(0, 0)
        bottom_right = self.index(len(self._data), len(self._data[0]))
        self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])
