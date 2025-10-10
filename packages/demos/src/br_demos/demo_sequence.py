import time
from pathlib import Path

from br_tester.config import AppConfig
from br_tester.parse_steps import steps_from_file
from br_tester.sequence import Sequence
from br_tester.br_logging import setup_logger


class DemoSequence(Sequence):
    def sequence(self):
        self.step(self.step_1, step_name="Step 1. Boolean Spec")
        self.step(self.step_2, step_name="Step 2. Boolean Spec")
        self.step(self.step_3, step_name="Step 3. No Specs")
        self.step(lambda: 1, step_name="Step 4. Lower limit")
        self.step(lambda: -1, step_name="Step 5. Upper limit")
        self.step(lambda: 0, step_name="Step 6. Equality (use lower limit)")
        self.step(lambda: 0.5, step_name="Step 7. Lower and upper limit")

    def step_1(self):
        return True

    def step_2(self):
        time.sleep(1)
        return True

    def step_3(self):
        time.sleep(1)
        self.logger.info("Step 3 executed")


if __name__ == "__main__":
    json_path = Path(__file__).parent / "demo_steps.json"
    steps = steps_from_file(json_path)
    AppConfig.load(profile="dev", config_dirs=["./config"])
    setup_logger()
    sequence = DemoSequence(steps)
    sequence.run()

