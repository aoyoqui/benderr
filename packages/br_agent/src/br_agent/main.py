import asyncio
from pathlib import Path

from br_agent.agent import Agent, SeqStatus
from rich.console import Console
from rich.table import Table

console = Console()

async def main_async():
    sequence_plan = ["demo-sequence", "demo-sequence"]
    config_path = Path("packages/demos/src/br_demos/demo_steps.json").resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    agent = Agent(sequence_plan, {name: config_path for name in sequence_plan})

    while True:
        next_seq = agent.next_allowed()
        if next_seq is None:
            break
        await agent.start_sequence(next_seq)
        while agent.runtime[next_seq].status == SeqStatus.RUNNING:
            await asyncio.sleep(0.1)

    table = agent.status_table()

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


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
