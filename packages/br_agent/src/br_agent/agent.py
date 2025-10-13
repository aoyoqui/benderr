import asyncio, os, time
from datetime import datetime
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
        rt.started_at = datetime.now()
        rt.status = SeqStatus.RUNNING
        if rt.proc.stdout:
            rt.out_task = asyncio.create_task(self._forward_stream(rt.proc.stdout, is_err=False))
        if rt.proc.stderr:
            rt.err_task = asyncio.create_task(self._forward_stream(rt.proc.stderr, is_err=True))

        asyncio.create_task(self._wait_and_finalize(rt))
        return rt.pid

    async def _wait_and_finalize(self, rt: SeqRuntime):
        rc = await rt.proc.wait()
        rt.ended_at = datetime.now()
        rt.status = SeqStatus.COMPLETED if rc == 0 else SeqStatus.FAILED
        # let readers finish
        if rt.out_task:
            await rt.out_task
        if rt.err_task:
            await rt.err_task

    async def _forward_stream(self, stream: asyncio.StreamReader, is_err: bool):
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode().rstrip()
            if is_err:
                print(text, file=os.sys.stderr)
            else:
                print(text)
        
    def is_busy(self):
        return any(rt.status == SeqStatus.RUNNING for rt in self.runtime)

    def next_allowed(self):
        for i, _ in enumerate(self.sequence_names):
            if self.runtime[i].status == SeqStatus.PENDING:
                return i

    def status_table(self) -> list[dict[str, str]]:
        rows = []
        time_format = "%Y-%m-%d %H:%M:%S.%f"
        for i, name in enumerate(self.sequence_names):
            rt = self.runtime[i]
            rows.append({
                "sequence": name, "status": rt.status.value, "pid": str(rt.pid or ""),
                "started_at": f"{rt.started_at.strftime(time_format)}" if rt.started_at else "",
                "ended_at": f"{rt.ended_at.strftime(time_format)}" if rt.ended_at else "",
            })
        return rows

    def _spec_path(self, sequence_name):
        if sequence_name not in self.config:
            raise KeyError(f"No spec path configured for {sequence_name}")
        return self.config[sequence_name]
    
