from importlib.metadata import entry_points

from PySide6.QtCore import QObject, Slot


def get_sequence(name: str):
    eps = entry_points(group="sequences")
    matches = {ep.name: ep.load() for ep in eps}
    if name not in matches:
        raise ValueError(f"Sequence '{name}' not found. Available: {list(matches)}")
    return matches[name]


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

