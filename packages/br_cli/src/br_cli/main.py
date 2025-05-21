import argparse
from importlib.metadata import entry_points
from pathlib import Path

from rich.console import Console
from br_tester.configurator import steps_from_file
from br_tester.events import step_started, step_ended
from br_tester.br_types import Verdict

console = Console()

def handle_step_started(sender, step):
    console.rule(f"[bold blue]🟡 Step Start: {step.name}")

def handle_step_ended(sender, result):
    passed = result.verdict == Verdict.PASSED
    color = "green" if passed else "red"
    icon = "✅" if passed else "❌"
    console.print(f"{icon} [bold {color}]Step Complete: {result.name}[/bold {color}]")

    for m in result.results:
        m_color = "green" if m.passed else "red"
        m_icon = "✔️" if m.passed else "✖️"
        console.print(f"  {m_icon} [bold {m_color}]{m.spec.name}[/]: {m.value}")

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

    step_started.connect(handle_step_started)
    step_ended.connect(handle_step_ended)

    SequenceClass = get_sequence(args.sequence)
    sequence = SequenceClass(steps)
    sequence.run()

if __name__ == "__main__":
    main()
