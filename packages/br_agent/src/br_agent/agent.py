"""
. for now simply receives a list of sequence names, forget about the manifest for now 
. for each sequence name, fetch its specs. for now instead of fetching, simply return from a hard-coded dictionary that returns the path file of a json file that contains the sequence config 
. It tracks the execution status of each test sequence 
. It receives requests to start executing a sequence
. It provides some guard rails/checks to allow only the execution of the next sequence (other rules may come later) 
. Upon request of a new sequence, it creates a new env if needed, where it runs the test
. The test is run with its run method. This is run in a new worker. When the run method finishes, the worker exits cleanly 
. The SDK already takes care of tracking start/end/steps events. 
Assume there is already a gRPC mechanism, and that the agent only needs to subscribe. 
You can leave the subscription bits as a stub 
. The next sequence may be started
"""
import asyncio, os, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum
from br_agent.env_manager import EnvManager

class SeqStatus(str, Enum):
    PENDING="PENDING"; RUNNING="RUNNING"; COMPLETED="COMPLETED"; FAILED="FAILED"

@dataclass
class SeqRuntime:
    name: str
    cfg_path: Path
    status: SeqStatus = SeqStatus.PENDING
    pid: Optional[int] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    proc: Optional[asyncio.subprocess.Process] = field(default=None, repr=False)
    out_task: Optional[asyncio.Task] = field(default=None, repr=False)
    err_task: Optional[asyncio.Task] = field(default=None, repr=False)

class Agent:
    def __init__(self, sequence_names: list[str], config_map: dict[str, str]):
        self.sequence_names = sequence_names
        self.config = {k: Path(v).resolve() for k, v in config_map.items()}
        self.runtime : list[SeqRuntime] = []
        self.env_mgr = EnvManager(Path.home()/".agent/envs", Path("dist").resolve())

        for name in self.sequence_names:
            cfg = self._spec_path(name)
            self.runtime.append(SeqRuntime(name=name, cfg_path=cfg))

    async def start_sequence(self, index: int):
        allowed = self.runtime[self.next_allowed()].name
        name = self.runtime[index].name
        if allowed is None:
            raise RuntimeError("All sequences completed")
        if name != allowed:
            raise RuntimeError(f"Cannot start '{name}'. Next allowed is '{allowed}'")
        if self.is_busy():
            raise RuntimeError("A sequence is already running")
        
        rt = self.runtime[index]
        # The required wheels name would come from a manifest file
        py = self.env_mgr.ensure_env(
            sequence_name=name, 
            required_wheels=[
                "br_cli-0.1.0-py3-none-any.whl", 
                "br_demos-0.1.0-py3-none-any.whl", 
                "br_sdk-0.1.0-py3-none-any.whl"
            ],
        )

        cmd = [str(py), "-m", "br_cli.main", "--sequence", name, "--config", str(rt.cfg_path)]
        rt.proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        rt.pid = rt.proc.pid
        rt.started_at = time.time()
        rt.status = SeqStatus.RUNNING

        asyncio.create_task(self._wait_and_finalize(rt))
        return rt.pid

    async def _wait_and_finalize(self, rt: SeqRuntime):
        rc = await rt.proc.wait()
        rt.ended_at = time.time()
        rt.status = SeqStatus.COMPLETED if rc == 0 else SeqStatus.FAILED
        # let readers finish
        if rt.out_task: await rt.out_task
        if rt.err_task: await rt.err_task
        
    def is_busy(self):
        return any(rt.status == SeqStatus.RUNNING for rt in self.runtime)

    def next_allowed(self):
        for i, _ in enumerate(self.sequence_names):
            if self.runtime[i].status == SeqStatus.PENDING:
                return i

    def status_table(self) -> list[dict[str, str]]:
        rows = []
        for i, name in enumerate(self.sequence_names):
            rt = self.runtime[i]
            rows.append({
                "sequence": name, "status": rt.status.value, "pid": str(rt.pid or ""),
                "started_at": f"{int(rt.started_at)}" if rt.started_at else "",
                "ended_at": f"{int(rt.ended_at)}" if rt.ended_at else "",
            })
        return rows

    def _spec_path(self, sequence_name):
        if sequence_name not in self.config:
            raise KeyError(f"No spec path configured for {sequence_name}")
        return self.config[sequence_name]
    
