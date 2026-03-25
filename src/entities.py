from __future__ import annotations

from dataclasses import dataclass
import pygame as pg

from .constants import COL_ENEMY, COL_GATEKEEPER, COL_PLAYER
from .util import clamp


@dataclass
class Stats:
    max_hp: int
    dmg: int
    speed: float


@dataclass
class Player:
    pos: pg.Vector2
    vel: pg.Vector2
    radius: int = 6
    hp: int = 5
    stats: Stats | None = None
    invuln_ms: int = 0
    attack_cooldown_ms: int = 0

    def rect(self) -> pg.Rect:
        return pg.Rect(int(self.pos.x - self.radius), int(self.pos.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt: float) -> None:
        self.pos += self.vel * dt
        if self.invuln_ms > 0:
            self.invuln_ms = max(0, self.invuln_ms - int(dt * 1000))
        if self.attack_cooldown_ms > 0:
            self.attack_cooldown_ms = max(0, self.attack_cooldown_ms - int(dt * 1000))

    def draw(self, surf: pg.Surface) -> None:
        col = (255, 255, 255) if self.invuln_ms > 0 else COL_PLAYER
        pg.draw.circle(surf, col, (int(self.pos.x), int(self.pos.y)), self.radius)


@dataclass
class Enemy:
    pos: pg.Vector2
    radius: int = 6
    hp: int = 2
    speed: float = 25.0
    is_gatekeeper: bool = False

    def rect(self) -> pg.Rect:
        return pg.Rect(int(self.pos.x - self.radius), int(self.pos.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt: float, player_pos: pg.Vector2) -> None:
        d = player_pos - self.pos
        if d.length_squared() > 0.001:
            d = d.normalize()
        self.pos += d * self.speed * dt

    def draw(self, surf: pg.Surface) -> None:
        col = COL_GATEKEEPER if self.is_gatekeeper else COL_ENEMY
        pg.draw.circle(surf, col, (int(self.pos.x), int(self.pos.y)), self.radius)


def keep_in_bounds(pos: pg.Vector2, w: int, h: int, pad: int = 8) -> None:
    pos.x = clamp(pos.x, pad, w - pad)
    pos.y = clamp(pos.y, pad, h - pad)

