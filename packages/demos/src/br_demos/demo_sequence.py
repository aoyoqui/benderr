import time
from pathlib import Path

from br_sdk.br_logging import setup_logger
from br_sdk.config import AppConfig
from br_sdk.parse_steps import steps_from_file
from br_sdk.sequence import Sequence


class DemoSequence(Sequence):
    @Sequence.step("Step 1. Boolean Spec")
    def test_step_1(self):
        return True

    @Sequence.step("Step 2. Boolean Spec")
    def test_step_2(self):
        time.sleep(1)
        return True

    @Sequence.step("Step 3. No Specs")
    def test_step_3(self):
        time.sleep(1)
        self.logger.info("Step 3 executed")

    @Sequence.step("Step 4. Lower limit")
    def test_step_4(self):
        return 1

    @Sequence.step("Step 5. Upper limit")
    def test_step_5(self):
        return -1

    @Sequence.step("Step 6. Equality (use lower limit)")
    def test_step_6(self):
        return 0

    @Sequence.step("Step 7. Lower and upper limit")
    def test_step_7(self):
        return 0.5

    @Sequence.step("Step 8. Mixed results")
    def test_step_8(self):
        return [True, 0.75]

    @Sequence.step("Step 9. String equality")
    def test_step_9(self):
        return "Calibrated"


if __name__ == "__main__":
    json_path = Path(__file__).parent / "demo_steps.json"
    steps_definition = steps_from_file(json_path)
    AppConfig.load(profile="dev", config_dirs=["./config"])
    setup_logger()
    sequence = DemoSequence(
        steps_definition.steps,
        sequence_config=steps_definition.config,
    )
    sequence.run()
