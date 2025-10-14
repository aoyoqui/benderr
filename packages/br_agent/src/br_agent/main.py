import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

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

    while True:
        next_idx = agent.next_allowed()
        if next_idx is None:
            break
        await agent.start_sequence(next_idx)
        while agent.runtime[next_idx].status == SeqStatus.RUNNING:
            await asyncio.sleep(0.1)

    return agent.status_table()


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
    parser = build_parser()
    args = parser.parse_args()
    results = asyncio.run(run_plan(args.plan.resolve()))
    render_summary(results)


if __name__ == "__main__":
    main()
