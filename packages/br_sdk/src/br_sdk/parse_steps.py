import json
from dataclasses import dataclass, field
from typing import Any
from typing import Sequence as TypingSequence

from br_sdk.br_types import Step


@dataclass
class StepsDefinition:
    steps: list[Step] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


def _coerce_steps(raw_steps: TypingSequence[dict[str, Any]]) -> list[Step]:
    return [Step(**step) for step in raw_steps]


def steps_from_file(file_path) -> StepsDefinition:
    with open(file_path) as f:
        data = json.load(f)

    if isinstance(data, dict):
        config = data.get("config", {})
        raw_steps = data.get("steps", [])
    elif isinstance(data, list):
        config = {}
        raw_steps = data
    else:
        raise ValueError("Step configuration must be a list or dictionary with 'steps'")

    steps = _coerce_steps(raw_steps)
    return StepsDefinition(steps=steps, config=config)
