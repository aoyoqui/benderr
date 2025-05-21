import numbers
from abc import ABC, abstractmethod
from datetime import datetime

from br_tester.br_types import NumericSpec, BooleanSpec, Measurement, SpecMismatch, Step, StepCountError, StepResult, Verdict, NumericComparator, InvalidSpec
from br_tester.events import step_started, step_ended

class Sequence(ABC):
    def __init__(self, steps: list[Step]):
        self.steps = steps
        self.step_results = []
        self.count = 0

    def run(self):
        """Call run to execute a sequence. Do not call sequence directly"""
        self.sequence()
        if self.count != len(self.steps):
            raise StepCountError(f"Fewer steps to report({self.count}) than there are specified({len(self.steps)})!")

    @abstractmethod
    def sequence(self):
        """
        Derive from this and implement the steps in this method, wrapping steps in the form:
            self.step(f, arg1, arg2, arg3, kwarg1, kwarg2)
        """
        pass

    def step(self, f, *args, **kwargs):
        if self.count > len(self.steps) - 1:
            # To do: how to handle this error in the report. Create a new step?
            raise StepCountError(f"More steps to report({self.count+1}) than there are specified({len(self.steps)})!")
        step_started.send(self, step=self.steps[self.count])
        step_result = StepResult(self.steps[self.count].id, self.steps[self.count].name, datetime.now())
        try:
            result = Sequence._execute(f, *args, **kwargs)
            step_result = self._test(result, step_result)
        except Exception:
            step_result.verdict = Verdict.ABORTED
            raise
        finally:
            step_result.end_time = datetime.now()
            self.step_results.append(step_result)
            step_ended.send(self, result=step_result)
        self.count += 1
        return result

    def _execute(f, *args, **kwargs):
        if args is not None or kwargs is not None:
            result = f(*args, **kwargs) # deal with exceptions
        else:
            result = f()
        return result

    def _test(self, result, step_result: StepResult) -> StepResult:
        specs = self.steps[self.count].specs
        # How do we turn a list of Specs into a list of Measurement
        # First, we need to process the result in some way. What form can result have? WHat should we support??
        # Supported types:
        # - bool - Spec supported is check_if_true, check_if_fals. len(specs) == 1. Take name from Spec
        # - str - Spec supported StringSpec. len(specs) == 1. Take name from Spec
        # - num - Spec supported NumericSpec. len(specs) == 1. Take name from Spec
        # - dataclass - Convention to check for attribute name in dataclass and compare to that value 
        #               using the other supported datatypes. len(specs) >= number of attributes
        #               Nested dataclasses not supported
        # - tuple/list - If tuples of primitive types, use name from Spec, use same order as provided. Use with care
        #                If tuples of dataclasses, 
        if specs is None or len(specs) == 0:
            step_result.verdict = Verdict.PASSED
        elif isinstance(result, bool):
            step_result = self._test_boolean(result, specs, step_result)
        elif isinstance(result, numbers.Number):
            step_result = self._test_numeric(result, specs, step_result)
        else:
            pass
        return step_result

    def _test_boolean(self, result, specs, step_result: StepResult):
        if(len(specs) > 1):
            raise SpecMismatch(
                f"Result is a single boolean but more than one spec for this result has been defined: {specs}"
            )
        spec = specs[0]
        if isinstance(spec, BooleanSpec):
            passed = (spec.pass_if_true and result) or (not spec.pass_if_true and not result)
            step_result.verdict = Verdict.PASSED if passed else Verdict.FAILED
            step_result.results.append(Measurement(result, passed, spec))
        else:
            raise SpecMismatch(f"Result is a single boolean but spec does not define a boolean check: {spec}")
        return step_result

    def _test_numeric(self, result, specs, step_result: StepResult):
        if(len(specs) > 1):
            raise SpecMismatch(
                f"Result is a single number but more than one spec for this result has been defined: {specs}"
            )
        spec = specs[0]
        if isinstance(spec, NumericSpec):
            match spec.comparator:
                case NumericComparator.GT:
                    passed = result > spec.lower
                case NumericComparator.GE:
                    passed = result >= spec.lower
                case NumericComparator.LT:
                    passed = result < spec.upper
                case NumericComparator.LE:
                    passed = result <= spec.upper
                case NumericComparator.EQ:
                    passed = result == spec.lower
                case NumericComparator.NEQ:
                    passed = result != spec.lower
                case NumericComparator.GTLT:
                    passed = spec.lower < result < spec.upper
                case NumericComparator.GELT:
                    passed = spec.lower <= result < spec.upper
                case NumericComparator.GTLE:
                    passed = spec.lower < result <= spec.upper
                case NumericComparator.GELE:
                    passed = spec.lower <= result <= spec.upper
                case NumericComparator.LTGT:
                    passed = spec.lower > result or result > spec.upper
                case NumericComparator.LTGE:
                    passed = spec.lower > result or result >= spec.upper
                case NumericComparator.LEGT:
                    passed = spec.lower >= result or result > spec.upper
                case NumericComparator.LEGE:
                    passed = spec.lower >= result or result >= spec.upper

            step_result.verdict = Verdict.PASSED if passed else Verdict.FAILED
            step_result.results.append(Measurement(result, passed, spec))
        else:
            raise SpecMismatch(f"Result is a single number but spec does not define a numeric test: {spec}")
        return step_result
