import subprocess, venv, os, shutil
from pathlib import Path

class EnvManager:
    def __init__(self, root: Path, wheel_dir: Path, allow_online=True):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.wheel_dir = Path(wheel_dir)
        self.allow_online = allow_online
        self.uv_exe = shutil.which("uv")

    def ensure_env(self, sequence_name: str, required_wheels):
        env_dir = self.root / sequence_name
        py = env_dir / ("Scripts/python.exe" if os.name=="nt" else "bin/python")
        if not py.exists():
            venv.create(env_dir, with_pip=self.uv_exe is None, clear=True)  # uv doesn’t need pip present

        if self.uv_exe:
            cmd = [self.uv_exe, "pip", "install", "--python", str(py), "--find-links", str(self.wheel_dir)]
        else:
            cmd = [str(py), "-m", "pip", "install", "--find-links", str(self.wheel_dir)]

        if self.allow_online:
            cmd += ["--extra-index-url", "https://pypi.org/simple"]
        else:
            cmd += ["--no-index"]

        # Prefer local wheel files; otherwise pass spec as-is
        pkgs = [str(self.wheel_dir / p) if (self.wheel_dir / p).exists() else p for p in required_wheels]
        subprocess.run(cmd + pkgs, check=True)
        return py  # (or return your EnvHandle)
