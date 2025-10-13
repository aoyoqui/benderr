import asyncio
from br_agent.agent import Agent, SeqStatus

async def main():
    plan = ["demo-sequence", "demo-sequence"]
    cfg_map = {
        "demo-sequence": "packages/demos/src/br_demos/demo_steps.json",
    }
    agent = Agent(plan, cfg_map)

    await agent.start_sequence(0)

    while agent.runtime[0].status == SeqStatus.RUNNING:
        await asyncio.sleep(0.25)
    nxt = agent.next_allowed()
    if nxt:
        await agent.start_sequence(nxt)

    while any(rt.status == SeqStatus.RUNNING for rt in agent.runtime):
        await asyncio.sleep(0.25)

    print(agent.status_table())

if __name__ == "__main__":
    asyncio.run(main())
