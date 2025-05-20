import argparse
from importlib.metadata import entry_points
from pathlib import Path

from br_tester.configurator import steps_from_file


def get_sequence(name: str):
    eps = entry_points(group="sequences")
    matches = {ep.name: ep.load() for ep in eps}
    if name not in matches:
        raise ValueError(f"Sequence '{name}' not found. Available: {list(matches)}")
    return matches[name]

def main():
    parser = argparse.ArgumentParser(description="Run a test sequence.")
    parser.add_argument("--sequence", required=True, help="Entry point name for the sequence (e.g., demo-sequence)")
    parser.add_argument("--config", required=True, type=Path, help="Path to a steps config JSON file")
    args = parser.parse_args()

    steps = steps_from_file(args.config)

    SequenceClass = get_sequence(args.sequence)
    sequence = SequenceClass(steps)
    sequence.run()

if __name__ == "__main__":
    main()
