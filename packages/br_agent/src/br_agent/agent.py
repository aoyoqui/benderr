import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from br_agent.env_manager import EnvManager


class SeqStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class SeqRuntime:
    name: str
    cfg_path: Path
    status: SeqStatus = SeqStatus.PENDING
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    proc: Optional[asyncio.subprocess.Process] = field(default=None, repr=False)
    out_task: Optional[asyncio.Task] = field(default=None, repr=False)
    err_task: Optional[asyncio.Task] = field(default=None, repr=False)


@dataclass
class TestSpec:
    name: str
    config_path: Path

class Agent:
    def __init__(
        self,
        tests: list[TestSpec],
        env_manager: EnvManager,
        required_packages: list[str],
    ):
        self.env_mgr = env_manager
        self.required_packages = required_packages
        self.runtime: list[SeqRuntime] = []

        for spec in tests:
            cfg = spec.config_path
            if not cfg.exists():
                raise FileNotFoundError(f"Config file not found: {cfg}")
            self.runtime.append(SeqRuntime(name=spec.name, cfg_path=cfg))

    async def start_sequence(self, index: int):
        allowed_idx = self.next_allowed()
        if allowed_idx is None:
            raise RuntimeError("All sequences completed")
        if index != allowed_idx:
            raise RuntimeError(
                f"Cannot start '{self.runtime[index].name}'. "
                f"Next allowed is '{self.runtime[allowed_idx].name}'"
            )
        if self.is_busy():
            raise RuntimeError("A sequence is already running")
        
        rt = self.runtime[index]
        py = self.env_mgr.ensure_env(
            sequence_name=rt.name,
            requirements=self.required_packages,
        )

        cmd = [str(py), "-m", "br_cli.main", "--sequence", rt.name, "--config", str(rt.cfg_path)]
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
        for i, rt in enumerate(self.runtime):
            if rt.status == SeqStatus.PENDING:
                return i
        return None

    def status_table(self) -> list[dict[str, str]]:
        rows = []
        time_format = "%Y-%m-%d %H:%M:%S.%f"
        for rt in self.runtime:
            rows.append({
                "sequence": rt.name, "status": rt.status.value, "pid": str(rt.pid or ""),
                "started_at": f"{rt.started_at.strftime(time_format)}" if rt.started_at else "",
                "ended_at": f"{rt.ended_at.strftime(time_format)}" if rt.ended_at else "",
            })
        return rows
    
