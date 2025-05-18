import pytest
from br_tester.br_types import Sequence, Step

def test_sequence():
    sequence = Sequence([])
    assert(len(sequence) == 0)

    sequence = Sequence()
    assert(len(sequence) == 0)

    sequence = Sequence(None)
    assert(len(sequence) == 0)

    sequence = Sequence([Step(1, "")])
    assert(len(sequence) == 1)

    sequence = Sequence([Step(1, ""), Step(2, "")])
    assert(len(sequence) == 2)

    step = sequence[0]
    assert(step.id == 1)
    assert(step.name == "")

    step = sequence[1]
    assert(step.id == 2)
    assert(step.name == "")

    with pytest.raises(IndexError):
        sequence[2]
