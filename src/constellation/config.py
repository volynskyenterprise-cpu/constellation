from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .simple_yaml import load_yaml


@dataclass(frozen=True)
class ConfigBundle:
    root: Path
    files: dict[str, dict[str, Any]]


class ConfigurationLoader:
    def __init__(self, root: Path) -> None:
        self.root = root

    def load(self) -> ConfigBundle:
        config_dir = self.root / "config"
        files: dict[str, dict[str, Any]] = {}
        for path in sorted(config_dir.glob("*.yaml")):
            files[path.stem] = load_yaml(path)
        return ConfigBundle(root=self.root, files=files)
