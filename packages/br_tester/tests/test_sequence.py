import pytest
from br_tester.br_types import NumericComparator, NumericSpec, Spec, Step, StepCountError
from br_tester.sequence import Sequence


def step_1():
    print("This is step 1")

def step_2(some_number):
    print("This is step 2")

def step_3(some_number, some_string):
    print("This is step 3")

class TestSequence1(Sequence):
    __test__ = False
    def sequence(self):
        self.step(step_1)
        self.step(step_2, 1)
        self.step(step_3, 0, "foo")
    
def test_number_of_steps():
    steps = [
        Step(1000, "Step 1", [Spec("voltage", NumericSpec(NumericComparator.GTLT, 0, 10, "V"))]), 
        Step(2000, "Step 2", []), 
        Step(3000, "Step 3", [])
    ]
    sequence = TestSequence1(steps)
    sequence.run()
    assert(len(sequence.step_results) == len(sequence.steps))

def test_fewer_steps_than_configured():
    steps = [
        Step(1000, "Step 1", [Spec("voltage", NumericSpec(NumericComparator.GTLT, 0, 10, "V"))]), 
        Step(2000, "Step 2", []), 
        Step(3000, "Step 3", []),
        Step(4000, "Step 4", [])
    ]
    sequence = TestSequence1(steps)
    with pytest.raises(StepCountError):
        sequence.run()
        
def test_more_steps_than_configured():
    steps = [
        Step(1000, "Step 1", [Spec("voltage", NumericSpec(NumericComparator.GTLT, 0, 10, "V"))]), 
        Step(2000, "Step 2", []), 
    ]
    sequence = TestSequence1(steps)
    with pytest.raises(StepCountError):
        sequence.run()

if __name__ == "__main__":
    pytest.main() 
