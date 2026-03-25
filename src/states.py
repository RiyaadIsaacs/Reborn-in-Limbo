from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Protocol

import pygame as pg

from .constants import (
    COL_BG,
    COL_HP,
    COL_KARMA_NEG,
    COL_KARMA_POS,
    COL_TEXT,
    FPS,
    VIRTUAL_H,
    VIRTUAL_W,
)
from .entities import Enemy, Player, Stats, keep_in_bounds
from .input_map import InputMap
from .memory_fragments import FRAGMENTS, MemoryFragment
from .save_data import SaveData
from .ui import Button, draw_button, draw_panel, draw_text


class GameState(Protocol):
    def handle_event(self, e: pg.event.Event) -> None: ...
    def update(self, dt: float) -> "GameState | None": ...
    def draw(self, surf: pg.Surface) -> None: ...


@dataclass
class Shared:
    inp: InputMap
    save: SaveData
    font: pg.font.Font
    rng: random.Random


class LimboRunState:
    def __init__(self, shared: Shared) -> None:
        self.s = shared
        max_hp = 5 + self.s.save.max_hp_up
        dmg = 1 + self.s.save.dmg_up
        self.player = Player(pos=pg.Vector2(VIRTUAL_W / 2, VIRTUAL_H / 2), vel=pg.Vector2(0, 0), hp=max_hp, stats=Stats(max_hp=max_hp, dmg=dmg, speed=60.0))
        self.enemies: list[Enemy] = []
        self.karma_run: int = 0
        self._spawn_timer = 0.0
        self._fragments_seen = 0
        self._next_fragment_at = 4.0
        self._gatekeeper_spawned = False

        # Spawn a first enemy so the loop is not empty.
        self._spawn_enemy()

    def handle_event(self, e: pg.event.Event) -> None:
        self.s.inp.handle_event(e)

    def _spawn_enemy(self) -> None:
        x = self.s.rng.randint(16, VIRTUAL_W - 16)
        y = self.s.rng.randint(16, VIRTUAL_H - 16)
        self.enemies.append(Enemy(pos=pg.Vector2(x, y), hp=2, speed=22.0))

    def _spawn_gatekeeper(self) -> None:
        self.enemies.append(Enemy(pos=pg.Vector2(VIRTUAL_W / 2, 20), hp=6, speed=18.0, is_gatekeeper=True, radius=8))
        self._gatekeeper_spawned = True

    def update(self, dt: float) -> GameState | None:
        # Movement
        move = pg.Vector2(0, 0)
        if self.s.inp.down(pg.K_a) or self.s.inp.down(pg.K_LEFT):
            move.x -= 1
        if self.s.inp.down(pg.K_d) or self.s.inp.down(pg.K_RIGHT):
            move.x += 1
        if self.s.inp.down(pg.K_w) or self.s.inp.down(pg.K_UP):
            move.y -= 1
        if self.s.inp.down(pg.K_s) or self.s.inp.down(pg.K_DOWN):
            move.y += 1
        if move.length_squared() > 0.001:
            move = move.normalize()
        self.player.vel = move * (self.player.stats.speed if self.player.stats else 60.0)

        # Attack (simple radius hit)
        if self.s.inp.pressed(pg.K_SPACE) and self.player.attack_cooldown_ms == 0:
            self.player.attack_cooldown_ms = 250
            hit_r = 16
            hit_pos = self.player.pos
            dmg = self.player.stats.dmg if self.player.stats else 1
            for en in self.enemies:
                if (en.pos - hit_pos).length_squared() <= hit_r * hit_r:
                    en.hp -= dmg

        # Update entities
        self.player.update(dt)
        keep_in_bounds(self.player.pos, VIRTUAL_W, VIRTUAL_H)

        for en in self.enemies:
            en.update(dt, self.player.pos)
        self.enemies = [e for e in self.enemies if e.hp > 0]

        # Contact damage
        if self.player.invuln_ms == 0:
            for en in self.enemies:
                if (en.pos - self.player.pos).length_squared() <= (en.radius + self.player.radius) ** 2:
                    self.player.hp -= 1
                    self.player.invuln_ms = 650
                    break

        # Death -> hub (permadeath)
        if self.player.hp <= 0:
            # Add run karma into meta currency and save.
            self.s.save.karma += self.karma_run
            if self.s.save.karma < 0:
                self.s.save.karma = 0
            self.s.save.save()
            return KarmaHubState(self.s)

        # Spawning cadence
        self._spawn_timer += dt
        if self._spawn_timer >= 2.5 and len(self.enemies) < 5 and not self._gatekeeper_spawned:
            self._spawn_timer = 0.0
            self._spawn_enemy()

        # Trigger memory fragment overlay during run.
        self._next_fragment_at -= dt
        if self._next_fragment_at <= 0 and self._fragments_seen < 2:
            self._fragments_seen += 1
            self._next_fragment_at = 999.0
            frag = self.s.rng.choice(FRAGMENTS)
            return MemoryOverlayState(self.s, parent=self, fragment=frag)

        # Spawn gatekeeper when "enough" fragments happened and enemies are cleared.
        if self._fragments_seen >= 2 and not self._gatekeeper_spawned and len(self.enemies) == 0:
            self._spawn_gatekeeper()

        # Victory: gatekeeper defeated and was spawned.
        if self._gatekeeper_spawned and len(self.enemies) == 0:
            # Reward some karma for finishing.
            self.karma_run += 3
            self.s.save.karma += self.karma_run
            self.s.save.save()
            return VictoryState(self.s)

        return None

    def draw(self, surf: pg.Surface) -> None:
        surf.fill(COL_BG)
        self.player.draw(surf)
        for en in self.enemies:
            en.draw(surf)

        # HUD
        draw_text(surf, self.s.font, f"HP: {self.player.hp}/{self.player.stats.max_hp if self.player.stats else self.player.hp}", (6, 6), COL_TEXT)
        karma_col = COL_KARMA_POS if self.karma_run >= 0 else COL_KARMA_NEG
        draw_text(surf, self.s.font, f"Karma(run): {self.karma_run}", (6, 22), karma_col)
        draw_text(surf, self.s.font, "Move: WASD/Arrows  Attack: Space", (6, VIRTUAL_H - 14), (170, 170, 190))


class MemoryOverlayState:
    def __init__(self, shared: Shared, *, parent: LimboRunState, fragment: MemoryFragment) -> None:
        self.s = shared
        self.parent = parent
        self.fragment = fragment
        self.choice_idx = 0

        self._btns: list[Button] = []
        x = 50
        y = 98
        w = VIRTUAL_W - 100
        h = 18
        for i, ch in enumerate(self.fragment.choices):
            self._btns.append(Button(pg.Rect(x, y + i * (h + 6), w, h), ch.label))

    def handle_event(self, e: pg.event.Event) -> None:
        self.s.inp.handle_event(e)

    def update(self, dt: float) -> GameState | None:
        if self.s.inp.pressed(pg.K_ESCAPE):
            return self.parent

        if self.s.inp.pressed(pg.K_UP) or self.s.inp.pressed(pg.K_w):
            self.choice_idx = (self.choice_idx - 1) % len(self._btns)
        if self.s.inp.pressed(pg.K_DOWN) or self.s.inp.pressed(pg.K_s):
            self.choice_idx = (self.choice_idx + 1) % len(self._btns)

        if self.s.inp.pressed(pg.K_RETURN) or self.s.inp.pressed(pg.K_SPACE):
            choice = self.fragment.choices[self.choice_idx]
            self.parent.karma_run += choice.karma_delta
            # Resume run; schedule next fragment later.
            self.parent._next_fragment_at = 6.0
            return self.parent

        return None

    def draw(self, surf: pg.Surface) -> None:
        # Draw parent (frozen snapshot feel)
        self.parent.draw(surf)

        # Dim overlay
        dim = pg.Surface((VIRTUAL_W, VIRTUAL_H), pg.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surf.blit(dim, (0, 0))

        panel = pg.Rect(30, 34, VIRTUAL_W - 60, VIRTUAL_H - 68)
        draw_panel(surf, panel)
        draw_text(surf, self.s.font, self.fragment.title, (panel.x + 8, panel.y + 8))
        draw_text(surf, self.s.font, self.fragment.body, (panel.x + 8, panel.y + 26), (210, 210, 225))
        draw_text(surf, self.s.font, "Choose:", (panel.x + 8, panel.y + 52), (180, 180, 200))

        for i, btn in enumerate(self._btns):
            draw_button(surf, self.s.font, btn, focused=(i == self.choice_idx))

        draw_text(surf, self.s.font, "Enter/Space: select  Esc: close", (panel.x + 8, panel.bottom - 14), (170, 170, 190))


class KarmaHubState:
    def __init__(self, shared: Shared) -> None:
        self.s = shared
        self.choice_idx = 0

        self.btns: list[Button] = [
            Button(pg.Rect(40, 70, VIRTUAL_W - 80, 18), "Upgrade_MaxHP (cost 5)"),
            Button(pg.Rect(40, 96, VIRTUAL_W - 80, 18), "Upgrade_Damage (cost 5)"),
            Button(pg.Rect(40, 128, VIRTUAL_W - 80, 18), "Start_Run"),
        ]

    def handle_event(self, e: pg.event.Event) -> None:
        self.s.inp.handle_event(e)

    def update(self, dt: float) -> GameState | None:
        if self.s.inp.pressed(pg.K_UP) or self.s.inp.pressed(pg.K_w):
            self.choice_idx = (self.choice_idx - 1) % len(self.btns)
        if self.s.inp.pressed(pg.K_DOWN) or self.s.inp.pressed(pg.K_s):
            self.choice_idx = (self.choice_idx + 1) % len(self.btns)

        if self.s.inp.pressed(pg.K_RETURN) or self.s.inp.pressed(pg.K_SPACE):
            if self.choice_idx == 0:
                if self.s.save.karma >= 5:
                    self.s.save.karma -= 5
                    self.s.save.max_hp_up += 1
                    self.s.save.save()
            elif self.choice_idx == 1:
                if self.s.save.karma >= 5:
                    self.s.save.karma -= 5
                    self.s.save.dmg_up += 1
                    self.s.save.save()
            elif self.choice_idx == 2:
                return LimboRunState(self.s)

        return None

    def draw(self, surf: pg.Surface) -> None:
        surf.fill((14, 14, 20))
        draw_text(surf, self.s.font, "Karma Hub", (6, 6), COL_TEXT)
        draw_text(surf, self.s.font, f"Karma: {self.s.save.karma}", (6, 22), COL_KARMA_POS)
        draw_text(surf, self.s.font, f"Upgrades: +HP {self.s.save.max_hp_up}  +DMG {self.s.save.dmg_up}", (6, 38), (200, 200, 215))

        for i, b in enumerate(self.btns):
            draw_button(surf, self.s.font, b, focused=(i == self.choice_idx))

        draw_text(surf, self.s.font, "Enter/Space: select", (6, VIRTUAL_H - 14), (170, 170, 190))


class VictoryState:
    def __init__(self, shared: Shared) -> None:
        self.s = shared
        self.t = 0.0

    def handle_event(self, e: pg.event.Event) -> None:
        self.s.inp.handle_event(e)

    def update(self, dt: float) -> GameState | None:
        self.t += dt
        if self.s.inp.pressed(pg.K_RETURN) or self.s.inp.pressed(pg.K_SPACE):
            return KarmaHubState(self.s)
        return None

    def draw(self, surf: pg.Surface) -> None:
        surf.fill((10, 10, 16))
        draw_text(surf, self.s.font, "The Gatekeeper falls.", (60, 60))
        draw_text(surf, self.s.font, "For a moment, the curse loosens.", (40, 82), (200, 200, 215))
        draw_text(surf, self.s.font, "Enter/Space: return to hub", (40, 120), (170, 170, 190))

