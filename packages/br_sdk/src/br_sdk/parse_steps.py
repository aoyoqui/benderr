import json

from br_sdk.br_types import Step


def steps_from_file(file_path):
    with open(file_path) as f:
        data = json.load(f)

    steps = [Step(**step) for step in data]
    return steps
