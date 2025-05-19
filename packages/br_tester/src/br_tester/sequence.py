from abc import ABC, abstractmethod
from datetime import datetime

from br_tester.br_types import StepCountError, StepResult


class Sequence(ABC):
    def __init__(self, steps):
        self.steps = steps
        self.step_results = []
        self.count = 0

    def run(self):
        """Call run to execute a sequence. Do not call sequence directly"""
        self.sequence()
        if self.count != len(self.steps):
            raise StepCountError("Fewer steps to report than there are specified!")

    @abstractmethod
    def sequence(self):
        """Derive from this and implement the steps in this method"""
        pass

    def step(self, f, *args):
        if self.count > len(self.steps) - 1:
            raise StepCountError("More steps to report than there are specified!")
        print(f"{self.steps[self.count].id}: {self.steps[self.count].name}")
        print(f"Start time is {datetime.now()}")        
        if args is not None:
            result = f(*args) # deal with exceptions
        else:
            result = f()
        self._test(result)
        print(f"End time is {datetime.now()}")
        self.count += 1
        return result

    def _test(self, *result):
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
        print(f"Specs: {specs}")
        if specs is None:
            pass # Measurement result is passed
        elif isinstance(specs, bool):
            pass
        elif isinstance(specs, str):
            pass
        else:
            pass
        self.step_results.append(StepResult(self.steps[self.count].id, self.steps[self.count].name))
