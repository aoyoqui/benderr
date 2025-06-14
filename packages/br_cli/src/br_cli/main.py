import argparse
from importlib.metadata import entry_points
from pathlib import Path

from br_tester.br_types import Measurement, StepResult, Verdict, Step
from br_tester.configurator import steps_from_file
from br_tester.events import step_ended, step_started
from rich.console import Console
from rich.table import Table

console = Console()


def handle_step_started(sender, step: Step):
    console.rule(f"[bold blue]🟡 Step Start: {step.name}")


def handle_step_ended(sender, result: StepResult):
    passed = result.verdict == Verdict.PASSED
    color = "green" if passed else "red"
    icon = "✅" if passed else "❌"
    console.print(f"{icon} [bold {color}]Step Complete: {result.name}[/bold {color}]")

    table = Table(title="Measurement results")
    table.add_column("Passed")
    table.add_column("Step name")
    table.add_column("Value")
    table.add_column("Comparator")
    table.add_column("Lower")
    table.add_column("Upper")
    table.add_column("Units")
    for m in result.results:
        add_to_table(table, m)
    if result.results:
        console.print(table)


def add_to_table(table: Table, m: Measurement):
    m_color = "green" if m.passed else "red"
    m_icon = "✅" if m.passed else "❌"
    match m.spec.type:
        case "boolean":
            table.add_row(
                f"{m_icon}",
                f"[bold {m_color}]{m.spec.name}[/]",
                f"[{m_color}]{m.value}[/]",
                f"{m.spec.pass_if_true}",
                "",
                "",
                "",
            )
        case "numeric":
            table.add_row(
                f"{m_icon}",
                f"[bold {m_color}]{m.spec.name}[/]",
                f"[{m_color}]{m.value}[/]",
                f"{m.spec.comparator}",
                f"{m.spec.lower}",
                f"{m.spec.upper}",
                f"{m.spec.units}",
            )


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
