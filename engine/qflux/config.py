"""Loads configs/default.yaml (master doc §5.7)."""
from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


@lru_cache(maxsize=None)
def load_config(path: str | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)
