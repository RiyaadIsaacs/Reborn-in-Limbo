from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .util import get_save_path, load_json, save_json


@dataclass
class SaveData:
    karma: int = 0
    # Permanent upgrades (simple numbers for MVP)
    max_hp_up: int = 0
    dmg_up: int = 0

    @staticmethod
    def load(path: Path | None = None) -> "SaveData":
        path = path or get_save_path()
        raw: Any = load_json(path, default={})
        return SaveData(
            karma=int(raw.get("karma", 0)),
            max_hp_up=int(raw.get("max_hp_up", 0)),
            dmg_up=int(raw.get("dmg_up", 0)),
        )

    def save(self, path: Path | None = None) -> None:
        path = path or get_save_path()
        save_json(path, asdict(self))

