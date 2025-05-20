import pytest
from pathlib import Path
import json
from br_tester.br_types import Step, BooleanSpec


def get_file_path(filename):
    json_path = Path(__file__).parent / "test_steps" / filename
    return json_path

def load_steps(filename):
    json_path = get_file_path(filename)
    with open(json_path) as f:
        data = json.load(f)

    steps = [Step(**step) for step in data]
    return steps

def test_boolean_steps():
    steps = load_steps("boolean_steps.json")
    assert(len(steps) == 3)
    for i, s in enumerate(steps):
        assert(s.id == i+1)
        assert(len(s.specs) == 2)
        assert(isinstance(s.specs[0], BooleanSpec))
        assert(isinstance(s.specs[1], BooleanSpec))
    assert(steps[0].name == "Power-Up Check")
    assert(steps[1].name == "Safety State Verification")
    assert(steps[2].name == "System Ready Confirmation")

if __name__ == "__main__":
    pytest.main(args=["-v"]) 

