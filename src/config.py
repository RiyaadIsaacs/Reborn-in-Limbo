from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .util import load_json, save_json


def _config_path() -> Path:
    return Path("config.json")


@dataclass
class AppConfig:
    window_w: int = 960
    window_h: int = 540
    fullscreen: bool = False

    @staticmethod
    def load(path: Path | None = None) -> "AppConfig":
        path = path or _config_path()
        raw: Any = load_json(path, default={})
        cfg = AppConfig()
        cfg.window_w = int(raw.get("window_w", cfg.window_w))
        cfg.window_h = int(raw.get("window_h", cfg.window_h))
        cfg.fullscreen = bool(raw.get("fullscreen", cfg.fullscreen))
        # Basic sanity
        cfg.window_w = max(320, cfg.window_w)
        cfg.window_h = max(180, cfg.window_h)
        return cfg

    def save(self, path: Path | None = None) -> None:
        path = path or _config_path()
        save_json(path, asdict(self))

