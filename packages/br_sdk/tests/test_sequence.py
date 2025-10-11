import time
from datetime import datetime

import pytest
from br_sdk.br_logging import setup_logger
from br_sdk.br_types import (
    BooleanSpec,
    NumericComparator,
    NumericSpec,
    SpecMismatch,
    Step,
    StepCountError,
    StepResult,
    StringSpec,
    Verdict,
)
from br_sdk.config import AppConfig
from br_sdk.sequence import Sequence

AppConfig.load(profile="ci", config_dirs=["./config"])
setup_logger()

def step_1():
    print("This is step 1")


def step_2(some_number):
    print("This is step 2")


def step_3(some_number, some_string):
    print("This is step 3")


class TestSequenceStepCount(Sequence):
    __test__ = False

    @Sequence.step("Step 1")
    def test_step_1(self):
        step_1()

    @Sequence.step("Step 2")
    def test_step_2(self):
        step_2(1)

    @Sequence.step("Step 3")
    def test_step_3(self):
        step_3(0, "foo")


def test_sequence_init():
    with pytest.raises(StepCountError):
        TestSequenceStepCount([])


def test_number_of_steps():
    steps = [
        Step(1000, "Step 1", [NumericSpec("voltage", NumericComparator.GTLT, 0, 10, "V")]),
        Step(2000, "Step 2", []),
        Step(3000, "Step 3", []),
    ]
    step_count = len(steps)
    sequence = TestSequenceStepCount(steps)
    sequence.run()
    assert len(sequence.step_results) == step_count


def test_fewer_steps_than_configured():
    steps = [
        Step(1000, "Step 1", [NumericSpec("voltage", NumericComparator.GTLT, 0, 10, "V")]),
        Step(2000, "Step 2", []),
        Step(3000, "Step 3", []),
        Step(4000, "Step 4", []),
    ]
    with pytest.raises(StepCountError):
        TestSequenceStepCount(steps)


def test_more_steps_than_configured():
    steps = [
        Step(1000, "Step 1", [NumericSpec("voltage", NumericComparator.GTLT, 0, 10, "V")]),
        Step(2000, "Step 2", []),
    ]
    with pytest.raises(StepCountError):
        TestSequenceStepCount(steps)


def test_no_return():
    def step_function():
        pass

    result = Sequence._execute(step_function)
    assert result is None


def test_lambda():
    result = Sequence._execute(lambda x: x**2, 5)
    assert result == 25


def test_step_return_no_params():
    def step_function():
        return 3.14

    result = Sequence._execute(step_function)
    assert result == 3.14


def test_step_return_with_params():
    foo = 3.14159

    def step_function(bar):
        return bar

    result = Sequence._execute(step_function, foo)
    assert result == foo
    result = Sequence._execute(step_function, 1.0)
    assert result == 1.0
    result = Sequence._execute(step_function, "foo")
    assert result == "foo"


def test_step_return_with_many_params():
    _foo = True
    _bar = 2.0
    _foobar = (3.0, 5.0)

    def step_function(foo, bar, foobar):
        return foo

    result = Sequence._execute(step_function, _foo, _bar, _foobar)
    assert result == _foo


def test_step_multiple_return():
    _foo = 1.0

    def step_function(foo):
        return foo, foo * 2

    result = Sequence._execute(step_function, _foo)
    assert isinstance(result, tuple)
    assert result[0] == _foo
    assert result[1] == _foo * 2


def test_step_with_kwargs():
    _foo = 1.7
    _bar = True

    def step_function(foo, bar):
        return bar, foo

    result = Sequence._execute(step_function, bar=_bar, foo=_foo)
    assert isinstance(result[0], type(_bar)) and result[0] == _bar
    assert isinstance(result[1], type(_foo)) and result[1] == _foo


def test_step_with_args_kwargs():
    _foo = 2.9
    _bar = "bar"
    _foobar = False

    def step_function(foo, bar, foobar):
        return foobar, foo, bar

    result = Sequence._execute(step_function, _foo, foobar=_foobar, bar=_bar)
    assert isinstance(result[0], type(_foobar)) and result[0] == _foobar
    assert isinstance(result[1], type(_foo)) and result[1] == _foo
    assert isinstance(result[2], type(_bar)) and result[2] == _bar


class TestSequenceNoSpecs(Sequence):
    __test__ = False

    @Sequence.step("Step Add")
    def test_add(self):
        return (lambda x: x + 1)(3.0)

    @Sequence.step("Step Pi")
    def test_pi(self):
        return 3.14

    @Sequence.step("Step Print")
    def test_print(self):
        print("Foo")


def test_pass_no_specs():
    steps = [Step(1000, "Step Add", []), Step(2000, "Step Pi", []), Step(3000, "Step Print", [])]
    step_count = len(steps)
    sequence = TestSequenceNoSpecs(steps)
    sequence.run()
    assert len(sequence.step_results) == step_count
    for r in sequence.step_results:
        assert r.verdict == Verdict.PASSED


def test_boolean_spec_check():
    result = Sequence._boolean_spec_passes(False, BooleanSpec("ExpectedFalse", pass_if_true=False))
    assert isinstance(result, bool) and result
    result = Sequence._boolean_spec_passes(True, BooleanSpec("ExpectedTrue", pass_if_true=True))
    assert isinstance(result, bool) and result
    result = Sequence._boolean_spec_passes(False, BooleanSpec("ExpectedTrue", pass_if_true=True))
    assert isinstance(result, bool) and not result
    result = Sequence._boolean_spec_passes(True, BooleanSpec("ExpectedFalse", pass_if_true=False))
    assert isinstance(result, bool) and not result


class TestSequenceBooleanSpecs(Sequence):
    __test__ = False

    @Sequence.step("Step True")
    def test_false_expected_true(self):
        return False

    @Sequence.step("Step True")
    def test_true_expected_true(self):
        return True

    @Sequence.step("Step False")
    def test_false_expected_false(self):
        return False

    @Sequence.step("Step False")
    def test_true_expected_false(self):
        return True


def test_boolean_steps():
    steps = [
        Step(1, "Step True", [BooleanSpec("ExpectedTrue", pass_if_true=True)]),
        Step(2, "Step True", [BooleanSpec("ExpectedTrue", pass_if_true=True)]),
        Step(2, "Step False", [BooleanSpec("ExpectedFalse", pass_if_true=False)]),
        Step(2, "Step False", [BooleanSpec("ExpectedFalse", pass_if_true=False)]),
    ]
    step_count = len(steps)
    sequence = TestSequenceBooleanSpecs(steps)
    sequence.run()
    assert len(sequence.step_results) == step_count
    assert sequence.step_results[0].verdict == Verdict.FAILED
    assert sequence.step_results[1].verdict == Verdict.PASSED
    assert sequence.step_results[2].verdict == Verdict.PASSED
    assert sequence.step_results[3].verdict == Verdict.FAILED
    assert len(sequence.step_results[0].results) == 1
    assert len(sequence.step_results[1].results) == 1
    assert len(sequence.step_results[2].results) == 1
    assert len(sequence.step_results[3].results) == 1
    assert not sequence.step_results[0].results[0].value
    assert sequence.step_results[1].results[0].value
    assert not sequence.step_results[2].results[0].value
    assert sequence.step_results[3].results[0].value
    assert not sequence.step_results[0].results[0].passed
    assert sequence.step_results[1].results[0].passed
    assert sequence.step_results[2].results[0].passed
    assert not sequence.step_results[3].results[0].passed


def test_boolean_spec_mismatch():
    with pytest.raises(SpecMismatch):
        Sequence._test_boolean(
            True, [NumericSpec("voltage", NumericComparator.GTLT, 0, 10, "V")], StepResult(0, "foo")
        )

    with pytest.raises(SpecMismatch):
        Sequence._test_boolean(
            True, [BooleanSpec("ExpectedTrue", True), BooleanSpec("ExpectedFalse", False)], StepResult(0, "foo")
        )


class TestSequenceListPass(Sequence):
    __test__ = False

    @Sequence.step("List Step")
    def test_list(self):
        return [True, 1.5, "Done"]


def test_list_step_pass():
    steps = [
        Step(
            1,
            "List Step",
            [
                BooleanSpec("Bool True", pass_if_true=True),
                NumericSpec("Voltage", NumericComparator.GT, 1.0),
                StringSpec("Status", expected="Done", case_sensitive=True),
            ],
        )
    ]
    sequence = TestSequenceListPass(steps)
    sequence.run()
    assert sequence.step_results[0].verdict == Verdict.PASSED
    assert [m.value for m in sequence.step_results[0].results] == [True, 1.5, "Done"]
    assert all(m.passed for m in sequence.step_results[0].results)


class TestSequenceListFail(Sequence):
    __test__ = False

    @Sequence.step("List Step")
    def test_list(self):
        return [True, -1.0]


def test_list_step_fail():
    steps = [
        Step(
            1,
            "List Step",
            [
                BooleanSpec("Bool True", pass_if_true=True),
                NumericSpec("Voltage", NumericComparator.GT, 0.0),
            ],
        )
    ]
    sequence = TestSequenceListFail(steps)
    sequence.run()
    assert sequence.step_results[0].verdict == Verdict.FAILED
    assert [m.value for m in sequence.step_results[0].results] == [True, -1.0]
    assert sequence.step_results[0].results[0].passed
    assert not sequence.step_results[0].results[1].passed


class TestSequenceListMismatch(Sequence):
    __test__ = False

    @Sequence.step("List Step")
    def test_list(self):
        return [True, False]


def test_list_step_length_mismatch():
    steps = [
        Step(
            1,
            "List Step",
            [BooleanSpec("Bool True", pass_if_true=True)],
        )
    ]
    sequence = TestSequenceListMismatch(steps)
    with pytest.raises(SpecMismatch):
        sequence.run()


def test_list_step_type_mismatch():
    steps = [
        Step(
            1,
            "List Step",
            [
                BooleanSpec("Bool True", pass_if_true=True),
                BooleanSpec("Second Bool", pass_if_true=True),
            ],
        )
    ]
    sequence = TestSequenceListFail(steps)
    with pytest.raises(SpecMismatch):
        sequence.run()


class TestSequenceListUnsupported(Sequence):
    __test__ = False

    @Sequence.step("List Step")
    def test_list(self):
        return [True, "unexpected"]


def test_list_step_unsupported_type():
    steps = [
        Step(
            1,
            "List Step",
            [
                BooleanSpec("Bool True", pass_if_true=True),
                NumericSpec("Voltage", NumericComparator.GT, 0.0),
            ],
        )
    ]
    sequence = TestSequenceListUnsupported(steps)
    with pytest.raises(SpecMismatch):
        sequence.run()


def test_list_step_string_spec_mismatch():
    steps = [
        Step(
            1,
            "List Step",
            [
                BooleanSpec("Bool True", pass_if_true=True),
                NumericSpec("Voltage", NumericComparator.GT, 1.0),
                NumericSpec("Should be string", NumericComparator.GT, 0.0),
            ],
        )
    ]
    sequence = TestSequenceListPass(steps)
    with pytest.raises(SpecMismatch):
        sequence.run()


class TestSequenceString(Sequence):
    __test__ = False

    @Sequence.step("String Step")
    def test_string(self):
        return "Hello"


def test_string_step_pass():
    steps = [
        Step(
            1,
            "String Step",
            [
                StringSpec("Greeting", expected="Hello", case_sensitive=True),
            ],
        )
    ]
    sequence = TestSequenceString(steps)
    sequence.run()
    assert sequence.step_results[0].verdict == Verdict.PASSED
    assert sequence.step_results[0].results[0].passed
    assert sequence.step_results[0].results[0].value == "Hello"


def test_string_step_case_insensitive_pass():
    steps = [
        Step(
            1,
            "String Step",
            [
                StringSpec("Greeting", expected="hello", case_sensitive=False),
            ],
        )
    ]
    sequence = TestSequenceString(steps)
    sequence.run()
    assert sequence.step_results[0].verdict == Verdict.PASSED
    assert sequence.step_results[0].results[0].passed


def test_string_step_fail():
    steps = [
        Step(
            1,
            "String Step",
            [
                StringSpec("Greeting", expected="Bye", case_sensitive=True),
            ],
        )
    ]
    sequence = TestSequenceString(steps)
    sequence.run()
    assert sequence.step_results[0].verdict == Verdict.FAILED
    assert not sequence.step_results[0].results[0].passed


def test_string_spec_mismatch():
    steps = [
        Step(
            1,
            "String Step",
            [
                NumericSpec("Voltage", NumericComparator.GT, 0.0),
            ],
        )
    ]
    sequence = TestSequenceString(steps)
    with pytest.raises(SpecMismatch):
        sequence.run()


def delay_10ms():
    time.sleep(0.01)


class StartEndTimeCustomError(Exception):
    pass


def step_raise_exception():
    time.sleep(0.01)
    raise StartEndTimeCustomError()


class TestSequenceStartEndTime(Sequence):
    __test__ = False

    @Sequence.step("delay_10ms")
    def test_delay(self):
        delay_10ms()

    @Sequence.step("step_raise_exception")
    def test_raises(self):
        step_raise_exception()


def test_sequence_start_end_time():
    sequence = TestSequenceStartEndTime([Step(1, "delay_10ms"), Step(2, "step_raise_exception")])
    now = datetime.now()
    with pytest.raises(StartEndTimeCustomError):
        sequence.run()
    assert now <= sequence.step_results[0].start_time
    assert sequence.step_results[0].start_time < sequence.step_results[0].end_time
    assert now <= sequence.step_results[1].start_time
    assert sequence.step_results[0].end_time < sequence.step_results[1].start_time
    assert sequence.step_results[1].start_time < sequence.step_results[1].end_time


def test_numeric_spec_pass():
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GT, -1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(1, NumericSpec("Expect pass", NumericComparator.GE, 0))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(1, NumericSpec("Expect pass", NumericComparator.GE, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(1e2, NumericSpec("Expect pass", NumericComparator.LT, None, 100.1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0b101, NumericSpec("Expect pass", NumericComparator.LE, None, 5))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0b101, NumericSpec("Expect pass", NumericComparator.LE, None, 5.1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0xFF, NumericSpec("Expect pass", NumericComparator.EQ, 255))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0xFF, NumericSpec("Expect pass", NumericComparator.NEQ, 254))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GTLT, -2, 2))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GELT, -1, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GELT, 0, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GTLE, -1, 0))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GTLE, -1, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GELE, -1, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GELE, 0, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.GELE, -1, 0))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LTGT, 1, 2))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LTGT, -2, -1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LTGE, 1, 2))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LTGE, -1, 0))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LTGE, -2, -1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGT, 1, 2))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGT, 0, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGT, -2, -1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGE, 0, 1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGE, 1, 2))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGE, -2, -1))
    assert isinstance(result, bool) and result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect pass", NumericComparator.LEGE, -1, 0))
    assert isinstance(result, bool) and result


def test_numeric_spec_fail():
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GT, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GT, 0))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GE, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LT, None, -1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LT, None, 0))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LE, None, -1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.EQ, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLT, 1, 2))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLT, 0, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLT, -1, 0))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLT, -2, -1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GELT, 1, 2))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GELT, -1, 0))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GELT, -2, -1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLE, -2, -1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLE, 0, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GTLE, 1, 2))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GELE, -2, -1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.GELE, 1, 2))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LTGT, -1, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LTGT, 0, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LTGT, -1, 0))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LTGE, 0, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LTGE, -1, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LEGT, -1, 0))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LEGT, -1, 1))
    assert isinstance(result, bool) and not result
    result = Sequence._numeric_test_passes(0, NumericSpec("Expect fail", NumericComparator.LEGE, -1, 1))
    assert isinstance(result, bool) and not result


class TestSequenceNumericSpecs(Sequence):
    __test__ = False

    @Sequence.step("greater_than_zero")
    def test_gt(self):
        return 1.0

    @Sequence.step("not_equal_zero")
    def test_neq(self):
        return 0xFF

    @Sequence.step("range_fail_low")
    def test_range_fail_low(self):
        return -2

    @Sequence.step("range_fail_high")
    def test_range_fail_high(self):
        return 0


def test_numeric_steps():
    steps = [
        Step(1, "greater_than_zero", [NumericSpec("Expect pass", NumericComparator.GT, 0)]),
        Step(2, "not_equal_zero", [NumericSpec("Expect pass", NumericComparator.NEQ, 0)]),
        Step(3, "range_fail_low", [NumericSpec("Expect fail", NumericComparator.GTLE, 0, 1)]),
        Step(4, "range_fail_high", [NumericSpec("Expect fail", NumericComparator.LEGE, -2, 2)]),
    ]
    step_count = len(steps)
    sequence = TestSequenceNumericSpecs(steps)
    sequence.run()
    assert len(sequence.step_results) == step_count
    assert sequence.step_results[0].verdict == Verdict.PASSED
    assert sequence.step_results[1].verdict == Verdict.PASSED
    assert sequence.step_results[2].verdict == Verdict.FAILED
    assert sequence.step_results[3].verdict == Verdict.FAILED
    assert len(sequence.step_results[0].results) == 1
    assert len(sequence.step_results[1].results) == 1
    assert len(sequence.step_results[2].results) == 1
    assert len(sequence.step_results[3].results) == 1
    assert sequence.step_results[0].results[0].value == 1.0
    assert sequence.step_results[1].results[0].value == 255
    assert sequence.step_results[2].results[0].value == -2
    assert sequence.step_results[3].results[0].value == 0
    assert sequence.step_results[0].results[0].passed
    assert sequence.step_results[1].results[0].passed
    assert not sequence.step_results[2].results[0].passed
    assert not sequence.step_results[3].results[0].passed


class TestSequenceNumericSpecMismatch(Sequence):
    __test__ = False

    @Sequence.step("pi")
    def test_pi(self):
        return 3.14


def test_numeric_spec_mismatch():
    with pytest.raises(SpecMismatch):
        Sequence._test_numeric(1, [BooleanSpec("Foo", True)], StepResult(0, "foo"))

    with pytest.raises(SpecMismatch):
        Sequence._test_numeric(
            1,
            [
                NumericSpec("Expect fail", NumericComparator.LEGT, -1, 1),
                NumericSpec("Expect fail", NumericComparator.LEGT, -1, 1),
            ],
            StepResult(0, "foo"),
        )


if __name__ == "__main__":
    pytest.main(args=["-v"])
