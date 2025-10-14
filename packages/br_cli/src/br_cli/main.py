import argparse
from importlib.metadata import entry_points
from pathlib import Path

from br_sdk.br_logging import setup_logger
from br_sdk.br_types import Measurement, Step, StepResult, Verdict
from br_sdk.config import AppConfig
from br_sdk.events import EventSubscriber, shutdown_event_server
from br_sdk.parse_steps import steps_from_file
from br_sdk.report_json import JsonReportFormatter
from rich.console import Console
from rich.table import Table

console = Console()


def handle_step_started(step: Step):
    console.rule(f"[bold blue]🟡 Step Start: {step.name}")


def handle_step_ended(result: StepResult):
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
        case "string":
            table.add_row(
                f"{m_icon}",
                f"[bold {m_color}]{m.spec.name}[/]",
                f"[{m_color}]{m.value}[/]",
                "EQ",
            )
        case "none":
            table.add_row(
                f"{m_icon}",
                f"[bold {m_color}]{m.spec.name}[/]",
                f"[{m_color}]{m.value}[/]",
                f"{m.spec.action}",
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

    AppConfig.load(profile="cli", config_dirs=["./config"])
    setup_logger()
    steps_definition = steps_from_file(args.config)

    subscriber = EventSubscriber(
        on_step_started=handle_step_started,
        on_step_ended=handle_step_ended,
        on_log=lambda msg, level: None,
        start_server=True,
    )
    subscriber.start()

    SequenceClass = get_sequence(args.sequence)
    sequence = SequenceClass(
        steps_definition.steps,
        JsonReportFormatter(),
        sequence_config=steps_definition.config,
    )
    try:
        sequence.run()
    finally:
        subscriber.stop(grace_period=0.2)
        shutdown_event_server()


if __name__ == "__main__":
    main()
