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
    
def test_sequence_init():
    sequence = TestSequence1([])
    assert(len(sequence.steps) == 0)
    assert(sequence.count == 0)

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

def test_no_return():
    def step_function():
        pass
    result = Sequence._execute(step_function)
    assert(result is None)

def test_lambda():
    result = Sequence._execute(lambda x: x**2, 5)
    assert(result == 25)

def test_step_return_no_params():
    def step_function():
        return 3.14
    result = Sequence._execute(step_function)
    assert(result == 3.14)

def test_step_return_with_params():
    foo = 3.14159
    def step_function(bar):
        return bar
    result = Sequence._execute(step_function, foo)
    assert(result == foo)
    result = Sequence._execute(step_function, 1.0)
    assert(result == 1.0)
    result = Sequence._execute(step_function, "foo")
    assert(result == "foo")

def test_step_return_with_many_params():
    _foo = True
    _bar = 2.0
    _foobar = (3.0, 5.0)
    def step_function(foo, bar, foobar):
        return foo
    result = Sequence._execute(step_function, _foo, _bar, _foobar)
    assert(result == _foo)

def test_step_multiple_return():
    _foo = 1.0
    def step_function(foo):
        return foo, foo*2
    result = Sequence._execute(step_function, _foo)
    assert(isinstance(result, tuple))
    assert(result[0] == _foo)
    assert(result[1] ==_foo*2)

def test_step_with_kwargs():
    _foo = 1.7
    _bar = True
    def step_function(foo, bar):
        return bar, foo
    result = Sequence._execute(step_function, bar=_bar, foo=_foo)
    assert(isinstance(result[0], type(_bar)) and result[0] == _bar)
    assert(isinstance(result[1], type(_foo)) and result[1] == _foo)

def test_step_with_args_kwargs():
    _foo = 2.9
    _bar = "bar"
    _foobar = False
    def step_function(foo, bar, foobar):
        return foobar, foo, bar
    result = Sequence._execute(step_function, _foo, foobar=_foobar, bar=_bar)
    assert(isinstance(result[0], type(_foobar)) and result[0] == _foobar)
    assert(isinstance(result[1], type(_foo)) and result[1] == _foo)
    assert(isinstance(result[2], type(_bar)) and result[2] == _bar)

if __name__ == "__main__":
    pytest.main() 
