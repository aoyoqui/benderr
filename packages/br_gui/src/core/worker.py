from importlib.metadata import entry_points

from br_sdk.parse_steps import StepsDefinition
from PySide6.QtCore import QObject, Slot


def get_sequence(name: str):
    eps = entry_points(group="sequences")
    matches = {ep.name: ep.load() for ep in eps}
    if name not in matches:
        raise ValueError(f"Sequence '{name}' not found. Available: {list(matches)}")
    return matches[name]


class Worker(QObject):
    def __init__(self, sequence, steps_definition: StepsDefinition):
        super().__init__()
        self.selected_sequence = sequence
        self.steps_definition = steps_definition

    @Slot()
    def run(self):
        SequenceClass = get_sequence(self.selected_sequence)
        sequence = SequenceClass(
            self.steps_definition.steps,
            sequence_config=self.steps_definition.config,
        )
        sequence.run()
