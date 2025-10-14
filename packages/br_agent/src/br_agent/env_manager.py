import os
import shutil
import subprocess
import venv
from pathlib import Path


class EnvManager:
    def __init__(
        self,
        root: Path,
        find_links: Path | None = None,
        allow_online: bool = True,
        extra_index_urls: list[str] | None = None,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.find_links = Path(find_links).resolve() if find_links else None
        self.allow_online = allow_online
        self.uv_exe = shutil.which("uv")
        self.extra_index_urls = extra_index_urls or []

    def ensure_env(self, sequence_name: str, requirements: list[str]):
        env_dir = self.root / sequence_name
        py = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not py.exists():
            venv.create(env_dir, with_pip=self.uv_exe is None, clear=True)

        if not requirements:
            return py

        if self.uv_exe:
            cmd = [self.uv_exe, "pip", "install", "--python", str(py)]
        else:
            cmd = [str(py), "-m", "pip", "install"]

        if self.find_links:
            cmd += ["--find-links", str(self.find_links)]

        if self.allow_online:
            for url in self.extra_index_urls:
                cmd += ["--extra-index-url", url]
        else:
            cmd += ["--no-index"]

        # Prefer local wheel files; otherwise pass spec as-is
        pkgs: list[str] = []
        for req in requirements:
            if self.find_links:
                candidate = self.find_links / req
                if candidate.exists():
                    pkgs.append(str(candidate))
                    continue
            pkgs.append(req)

        subprocess.run(cmd + pkgs, check=True)
        return py
