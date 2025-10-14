from pathlib import Path

import pytest
from br_sdk.br_types import BooleanSpec, NumericComparator, NumericSpec
from br_sdk.parse_steps import steps_from_file


def get_file_path(filename):
    json_path = Path(__file__).parent / "test_steps" / filename
    return json_path


def test_boolean_steps():
    steps_definition = steps_from_file(get_file_path("boolean_steps.json"))
    steps = steps_definition.steps
    assert len(steps) == 3
    for i, s in enumerate(steps):
        assert s.id == i + 1
        assert len(s.specs) == 2
        assert isinstance(s.specs[0], BooleanSpec)
        assert isinstance(s.specs[1], BooleanSpec)
    assert steps[0].name == "Power-Up Check"
    assert steps[1].name == "Safety State Verification"
    assert steps[2].name == "System Ready Confirmation"


def test_steps_with_sequence_config(tmp_path):
    config_path = tmp_path / "steps_with_config.json"
    config_path.write_text(
        """
{
  "config": {"stop_at_step_fail": false},
  "steps": [
    {"id": 1, "name": "Example", "specs": []}
  ]
}
"""
    )
    steps_definition = steps_from_file(config_path)
    assert steps_definition.config == {"stop_at_step_fail": False}
    assert len(steps_definition.steps) == 1
    assert steps_definition.steps[0].name == "Example"


def test_numeric_spec_validation():
    with pytest.raises(ValueError):
        NumericSpec("foo", NumericComparator.EQ, 0, -1)
    with pytest.raises(ValueError):
        NumericSpec("foo", NumericComparator.GTLT, 0, -1)
    with pytest.raises(ValueError):
        NumericSpec("foo", NumericComparator.GT, None, -1)
    with pytest.raises(ValueError):
        NumericSpec("foo", NumericComparator.LT, 0)


if __name__ == "__main__":
    pytest.main(args=["-v"])
