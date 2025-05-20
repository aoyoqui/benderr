import pytest
from pathlib import Path
from br_tester.br_types import BooleanSpec
from br_tester.configurator import steps_from_file

def get_file_path(filename):
    json_path = Path(__file__).parent / "test_steps" / filename
    return json_path


def test_boolean_steps():
    steps = steps_from_file(get_file_path("boolean_steps.json"))
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

