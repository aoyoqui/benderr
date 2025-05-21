from pathlib import Path

from br_tester.configurator import steps_from_file
from br_tester.sequence import Sequence


class DemoSequence(Sequence):
    def sequence(self):
        self.step(self.step_1)
        self.step(self.step_2)
        self.step(self.step_3)

    def step_1(self):
        return True
    
    def step_2(self):
        return False

    def step_3(self):
        pass

if __name__ == "__main__":
    json_path = Path(__file__).parent / "demo_steps.json"
    steps = steps_from_file(json_path) 
    sequence = DemoSequence(steps)
    sequence.run()
