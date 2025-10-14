import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from br_sdk.br_types import Step, StepResult
from br_sdk.config import AppConfig
from br_sdk.events import EventSubscriber, shutdown_event_server
from rich.console import Console
from rich.table import Table

from br_agent.agent import Agent, SeqStatus, TestSpec
from br_agent.env_manager import EnvManager


@dataclass
class PackagePlan:
    env_root: Path
    find_links: Path | None
    allow_online: bool
    extra_index_urls: list[str]
    requirements: list[str]


@dataclass
class Plan:
    packages: PackagePlan
    tests: list[TestSpec]


console = Console()


def load_plan(path: Path) -> Plan:
    with path.open() as f:
        data = json.load(f)

    try:
        tests_data = data["tests"]
    except KeyError as exc:
        raise ValueError("Plan file must contain a 'tests' list") from exc

    packages_data = data.get("packages", {})

    def resolve_path(value: str | None) -> Path | None:
        if value is None:
            return None
        p = Path(value).expanduser()
        if not p.is_absolute():
            p = (path.parent / p).resolve()
        return p

    env_root = resolve_path(packages_data.get("env_root")) or Path.home() / ".agent/envs"
    find_links = resolve_path(packages_data.get("find_links"))
    allow_online = packages_data.get("allow_online", False)
    extra_index_urls = list(packages_data.get("extra_index_urls", []))
    requirements = list(packages_data.get("requirements", []))

    package_plan = PackagePlan(
        env_root=env_root,
        find_links=find_links,
        allow_online=allow_online,
        extra_index_urls=extra_index_urls,
        requirements=requirements,
    )

    tests: list[TestSpec] = []
    for entry in tests_data:
        name = entry.get("name")
        config = entry.get("config")
        if not name or not config:
            raise ValueError("Each test entry must include 'name' and 'config' fields")
        config_path = resolve_path(config)
        if config_path is None or not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config}")
        tests.append(TestSpec(name=name, config_path=config_path))

    if not tests:
        raise ValueError("Plan contains no tests to execute")

    return Plan(packages=package_plan, tests=tests)


async def run_plan(plan_path: Path):
    plan = load_plan(plan_path)

    env_manager = EnvManager(
        root=plan.packages.env_root,
        find_links=plan.packages.find_links,
        allow_online=plan.packages.allow_online,
        extra_index_urls=plan.packages.extra_index_urls,
    )

    agent = Agent(
        tests=plan.tests,
        env_manager=env_manager,
        required_packages=plan.packages.requirements,
    )

    captured_events: list[dict[str, str]] = []

    def record_step_started(step: Step):
        captured_events.append(
            {
                "type": "started",
                "id": str(step.id),
                "name": step.name,
            }
        )

    def record_step_ended(result: StepResult):
        captured_events.append(
            {
                "type": "ended",
                "id": str(result.id),
                "name": result.name,
                "verdict": result.verdict.value,
            }
        )

    def record_log(message: str, level: str):
        captured_events.append(
            {
                "type": "log",
                "level": level,
                "message": message,
            }
        )

    subscriber = EventSubscriber(
        on_step_started=record_step_started,
        on_step_ended=record_step_ended,
        on_log=record_log,
        start_server=True,
    )
    subscriber.start()
    subscriber.wait_until_ready(timeout=5.0)

    while True:
        next_idx = agent.next_allowed()
        if next_idx is None:
            break
        await agent.start_sequence(next_idx)
        while agent.runtime[next_idx].status == SeqStatus.RUNNING:
            await asyncio.sleep(0.1)

    table = agent.status_table()

    subscriber.stop(grace_period=0.2)
    shutdown_event_server()

    return table, captured_events


def render_summary(table: list[dict[str, str]]):
    console.rule("[bold]Summary")
    summary = Table(show_header=True, header_style="bold magenta")
    summary.add_column("Sequence")
    summary.add_column("Status")
    summary.add_column("PID")
    summary.add_column("Started")
    summary.add_column("Ended")
    for row in table:
        summary.add_row(
            row["sequence"],
            row["status"],
            row["pid"],
            row["started_at"],
            row["ended_at"],
        )
    console.print(summary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent test runner")
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="Path to a JSON file describing the test plan",
    )
    return parser


def main():
    AppConfig.load(profile="cli", config_dirs=["./config"])
    parser = build_parser()
    args = parser.parse_args()
    results, events = asyncio.run(run_plan(args.plan.resolve()))
    render_summary(results)
    if events:
        console.rule("[bold]Captured Events")
        events_table = Table(show_header=True, header_style="bold cyan")
        events_table.add_column("Type")
        events_table.add_column("ID")
        events_table.add_column("Name / Message")
        events_table.add_column("Verdict / Level")
        for event in events:
            match event["type"]:
                case "started":
                    events_table.add_row("started", event["id"], event["name"], "")
                case "ended":
                    events_table.add_row("ended", event["id"], event["name"], event.get("verdict", ""))
                case "log":
                    events_table.add_row("log", "", event["message"], event.get("level", ""))
        console.print(events_table)


if __name__ == "__main__":
    main()
