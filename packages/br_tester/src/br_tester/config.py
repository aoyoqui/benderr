from pathlib import Path

import yaml


class AppConfig:
    _config = {}
    _loaded = False

    @classmethod
    def load(cls, profile='dev', config_dirs=None):
        cls._config = {}
        config_dirs = config_dirs or ["./config"]
        filenames = ["base.yaml", f"{profile}.yaml"]

        for dir in config_dirs:
            for filename in filenames:
                path = Path(dir) / filename
                if path.exists():
                    with open(path) as f:
                        data = yaml.safe_load(f) or {}
                        cls._merge(cls._config, data)

        cls._loaded = True

    @classmethod
    def get(cls, key, default=None):
        if not cls._loaded:
            raise RuntimeError("AppConfig not loaded. Call AppConfig.load() first")
        return cls._config.get(key, default)

    @staticmethod
    def _merge(dest: dict, src: dict):
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dest.get(key), dict):
                AppConfig._merge(dest[key], value)
            else:
                dest[key]= value
