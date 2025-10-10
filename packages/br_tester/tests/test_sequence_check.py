import pytest

from br_tester.br_types import Step, StepCountError, StepsConfigError
from br_tester.sequence import Sequence


class TestSequenceOrdering(Sequence):
    __test__ = False

    @Sequence.step("Step One")
    def test_first(self):
        return True

    @Sequence.step("Step Two")
    def test_second(self):
        return False


def test_registered_steps_in_order():
    steps = [Step(1, "Step One"), Step(2, "Step Two")]
    sequence = TestSequenceOrdering(steps)

    registered_names = [entry["config_name"] for entry in sequence._registered_steps]
    assert registered_names == ["Step One", "Step Two"]


class TestSequenceMissingDecorator(Sequence):
    __test__ = False

    def test_missing_decorator(self):
        return True


def test_missing_decorator_raises():
    steps = [Step(1, "Step One")]
    with pytest.raises(StepsConfigError):
        TestSequenceMissingDecorator(steps)


class TestSequenceNameMismatch(Sequence):
    __test__ = False

    @Sequence.step("Configured Name")
    def test_step(self):
        return True


def test_step_name_mismatch():
    steps = [Step(1, "Different Name")]
    with pytest.raises(StepsConfigError):
        TestSequenceNameMismatch(steps)


class TestSequenceCountMismatch(Sequence):
    __test__ = False

    @Sequence.step("Only Step")
    def test_only(self):
        return True


def test_step_count_mismatch():
    steps = [Step(1, "Only Step"), Step(2, "Extra")]
    with pytest.raises(StepCountError):
        TestSequenceCountMismatch(steps)
