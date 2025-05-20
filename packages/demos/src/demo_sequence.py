from pathlib import Path
from br_tester.sequence import Sequence
from br_tester.configurator import steps_from_file

class DemoSequence(Sequence):
    def sequence(self):
        self.step(self.step_1)
        self.step(self.step_2)
        self.step(self.step_3)

    def step_1(self):
        print("I am executing step 1")

    def step_2(self):
        print("I am executing step 2")

    def step_3(self):
        print("I am executing step 3")

if __name__ == "__main__":
    json_path = Path(__file__).parent / "demo_steps.json"
    steps = steps_from_file(json_path) 
    sequence = DemoSequence(steps)
    sequence.run()
