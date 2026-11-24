"""配置与项目上下文。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class Project:
    root: Path
    cfg: dict

    @classmethod
    def load(cls, root: str | Path = ".") -> "Project":
        root = Path(root).expanduser().resolve()
        path = root / "config" / "project.yaml"
        if not path.exists():
            raise FileNotFoundError(f"未找到项目配置：{path}")
        return cls(root=root, cfg=yaml.safe_load(path.read_text(encoding="utf-8")))

    @property
    def name(self) -> str:
        return self.cfg.get("name", self.root.name)

    def data_path(self, key: str) -> Path:
        p = self.root / self.cfg["data"][key]
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def load_config(self, name: str) -> dict:
        p = self.root / "config" / f"{name}.yaml"
        if not p.exists():
            return {}
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    def save_config(self, name: str, data: dict) -> Path:
        p = self.root / "config" / f"{name}.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return p

    def db(self):
        import duckdb
        return duckdb.connect(str(self.data_path("database")))

    def log(self, msg: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
        print(line)
        lp = self.root / "logs" / "run.log"
        lp.parent.mkdir(parents=True, exist_ok=True)
        with lp.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
