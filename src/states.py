from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Protocol

import pygame as pg

from .config import AppConfig
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
from .ui import Button, draw_button, draw_panel, draw_text, layout_vstack, draw_wrapped_text
from .dungeon_gen import Dungeon, generate_dungeon


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
    cfg: "AppConfig"
    window_request: "WindowRequest | None" = None


@dataclass
class WindowRequest:
    window_w: int
    window_h: int
    fullscreen: bool = False


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

        # World + camera
        self._cell = 8
        # Bigger world than viewport so camera matters.
        self._grid_w = 120
        self._grid_h = 80
        self._world_w = self._grid_w * self._cell
        self._world_h = self._grid_h * self._cell
        self._cam = pg.Vector2(0, 0)

        # Generate a random dungeon each run (3-5 rooms), with larger rooms.
        self.dungeon: Dungeon = generate_dungeon(
            rng=self.s.rng,
            grid_w=self._grid_w,
            grid_h=self._grid_h,
            room_w_range=(12, 18),
            room_h_range=(9, 14),
            corridor_width=2,
        )
        self._tiles: list[list[int]] = [[0 for _ in range(self._grid_w)] for _ in range(self._grid_h)]
        self._build_dungeon_tiles()
        self._spawn_room_enemies()

        # Start player in room 1 center (or fallback).
        try:
            cx, cy = self.dungeon.rooms[0].rect.center()
            self.player.pos = pg.Vector2(cx * self._cell, cy * self._cell)
        except Exception:
            self.player.pos = pg.Vector2(self._world_w / 2, self._world_h / 2)

    def handle_event(self, e: pg.event.Event) -> None:
        self.s.inp.handle_event(e)

    def _spawn_enemy(self) -> None:
        # Spawn an enemy inside a random room interior.
        if not self.dungeon.rooms:
            return
        room = self.s.rng.choice(self.dungeon.rooms)
        r = room.rect
        ix0, iy0 = r.x + 1, r.y + 1
        ix1, iy1 = r.x + r.w - 2, r.y + r.h - 2
        if ix1 <= ix0 or iy1 <= iy0:
            return
        gx = self.s.rng.randint(ix0, ix1)
        gy = self.s.rng.randint(iy0, iy1)
        self.enemies.append(Enemy(pos=pg.Vector2(gx * self._cell, gy * self._cell), hp=2, speed=22.0))

    def _build_dungeon_tiles(self) -> None:
        # 0 empty, 1 floor, 2 wall
        for room in self.dungeon.rooms:
            r = room.rect
            for yy in range(r.y, r.y + r.h):
                for xx in range(r.x, r.x + r.w):
                    is_wall = yy in (r.y, r.y + r.h - 1) or xx in (r.x, r.x + r.w - 1)
                    if 0 <= xx < self._grid_w and 0 <= yy < self._grid_h:
                        self._tiles[yy][xx] = 2 if is_wall else 1

        for cor in self.dungeon.corridors:
            self._stamp_corridor(cor.a, cor.b, cor.width)

    def _stamp_corridor(self, a: tuple[int, int], b: tuple[int, int], w: int) -> None:
        ax, ay = a
        bx, by = b
        mid = (bx, ay) if self.s.rng.random() < 0.5 else (ax, by)
        for p0, p1 in ((a, mid), (mid, b)):
            x0, y0 = p0
            x1, y1 = p1
            if x0 == x1:
                y_start, y_end = (y0, y1) if y0 <= y1 else (y1, y0)
                for yy in range(y_start, y_end + 1):
                    for dx in range(-w + 1, w):
                        xx = x0 + dx
                        if 0 <= xx < self._grid_w and 0 <= yy < self._grid_h:
                            self._tiles[yy][xx] = 1
            elif y0 == y1:
                x_start, x_end = (x0, x1) if x0 <= x1 else (x1, x0)
                for xx in range(x_start, x_end + 1):
                    for dy in range(-w + 1, w):
                        yy = y0 + dy
                        if 0 <= xx < self._grid_w and 0 <= yy < self._grid_h:
                            self._tiles[yy][xx] = 1

    def _spawn_room_enemies(self) -> None:
        # Spawn enemies based on room index; later rooms have more enemies.
        for room in self.dungeon.rooms:
            r = room.rect
            inner_x0 = r.x + 1
            inner_y0 = r.y + 1
            inner_x1 = r.x + r.w - 2
            inner_y1 = r.y + r.h - 2
            if inner_x1 <= inner_x0 or inner_y1 <= inner_y0:
                continue
            for _ in range(room.enemy_count):
                gx = self.s.rng.randint(inner_x0, inner_x1)
                gy = self.s.rng.randint(inner_y0, inner_y1)
                self.enemies.append(Enemy(pos=pg.Vector2(gx * self._cell, gy * self._cell), hp=2, speed=22.0))

    def _spawn_gatekeeper(self) -> None:
        # Spawn in the last room center.
        if self.dungeon.rooms:
            cx, cy = self.dungeon.rooms[-1].rect.center()
            pos = pg.Vector2(cx * self._cell, cy * self._cell)
        else:
            pos = pg.Vector2(self._world_w / 2, self._world_h / 2)
        self.enemies.append(Enemy(pos=pos, hp=6, speed=18.0, is_gatekeeper=True, radius=8))
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
        old_pos = self.player.pos.copy()
        self.player.update(dt)
        # Bound to world
        keep_in_bounds(self.player.pos, self._world_w, self._world_h)
        # Prevent walking into walls: if player's center is in a wall tile, push back.
        gx = int(self.player.pos.x) // self._cell
        gy = int(self.player.pos.y) // self._cell
        if 0 <= gx < self._grid_w and 0 <= gy < self._grid_h and self._tiles[gy][gx] == 2:
            self.player.pos = old_pos

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
        if self._spawn_timer >= 2.5 and len(self.enemies) < 10 and not self._gatekeeper_spawned:
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

    def _update_camera(self) -> None:
        # Center camera on player, clamp to world bounds.
        target_x = self.player.pos.x - VIRTUAL_W / 2
        target_y = self.player.pos.y - VIRTUAL_H / 2
        target_x = max(0, min(self._world_w - VIRTUAL_W, target_x))
        target_y = max(0, min(self._world_h - VIRTUAL_H, target_y))
        self._cam.update(target_x, target_y)

    def draw(self, surf: pg.Surface) -> None:
        surf.fill(COL_BG)
        self._update_camera()

        floor_col = (45, 48, 64)
        wall_col = (90, 70, 120)

        # Visible tile range only (camera culling)
        x0 = max(0, int(self._cam.x) // self._cell - 1)
        y0 = max(0, int(self._cam.y) // self._cell - 1)
        x1 = min(self._grid_w, (int(self._cam.x) + VIRTUAL_W) // self._cell + 2)
        y1 = min(self._grid_h, (int(self._cam.y) + VIRTUAL_H) // self._cell + 2)

        for y in range(y0, y1):
            for x in range(x0, x1):
                t = self._tiles[y][x]
                if t == 0:
                    continue
                col = floor_col if t == 1 else wall_col
                rx = x * self._cell - int(self._cam.x)
                ry = y * self._cell - int(self._cam.y)
                pg.draw.rect(surf, col, pg.Rect(rx, ry, self._cell, self._cell))

        # Draw entities with camera offset
        px = int(self.player.pos.x - self._cam.x)
        py = int(self.player.pos.y - self._cam.y)
        pcol = (255, 255, 255) if self.player.invuln_ms > 0 else (120, 210, 255)
        pg.draw.circle(surf, pcol, (px, py), self.player.radius)

        for en in self.enemies:
            ex = int(en.pos.x - self._cam.x)
            ey = int(en.pos.y - self._cam.y)
            if ex < -20 or ey < -20 or ex > VIRTUAL_W + 20 or ey > VIRTUAL_H + 20:
                continue
            ecol = (140, 80, 200) if en.is_gatekeeper else (200, 110, 160)
            pg.draw.circle(surf, ecol, (ex, ey), en.radius)

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

        x = 50
        w = VIRTUAL_W - 100
        y = 86
        area_h = VIRTUAL_H - y - 34
        rects = layout_vstack(x=x, y=y, w=w, h=area_h, count=len(self.fragment.choices), item_h=16, gap=6)
        self._btns = [Button(r, ch.label) for r, ch in zip(rects, self.fragment.choices, strict=False)]

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
        body_rect = pg.Rect(panel.x + 8, panel.y + 24, panel.w - 16, 44)
        y_after = draw_wrapped_text(surf, self.s.font, self.fragment.body, body_rect, color=(210, 210, 225), line_gap=1, max_lines=4)
        draw_text(surf, self.s.font, "Choose:", (panel.x + 8, max(panel.y + 52, y_after + 4)), (180, 180, 200))

        for i, btn in enumerate(self._btns):
            draw_button(surf, self.s.font, btn, focused=(i == self.choice_idx))

        draw_text(surf, self.s.font, "Enter/Space: select  Esc: close", (panel.x + 8, panel.bottom - 14), (170, 170, 190))


class KarmaHubState:
    def __init__(self, shared: Shared) -> None:
        self.s = shared
        self.choice_idx = 0
        self._labels = [
            "Upgrade_MaxHP (cost 5)",
            "Upgrade_Damage (cost 5)",
            "Settings (Resolution)",
            "Start_Run",
        ]
        self.btns: list[Button] = [Button(pg.Rect(0, 0, 0, 0), lab) for lab in self._labels]

    def _relayout(self) -> None:
        rects = layout_vstack(
            x=40,
            y=58,
            w=VIRTUAL_W - 80,
            h=VIRTUAL_H - 58 - 20,
            count=len(self.btns),
            item_h=16,
            gap=6,
        )
        for b, r in zip(self.btns, rects, strict=False):
            b.rect = r

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
                return SettingsState(self.s)
            elif self.choice_idx == 3:
                return LimboRunState(self.s)

        return None

    def draw(self, surf: pg.Surface) -> None:
        surf.fill((14, 14, 20))
        draw_text(surf, self.s.font, "Karma Hub", (6, 6), COL_TEXT)
        draw_text(surf, self.s.font, f"Karma: {self.s.save.karma}", (6, 22), COL_KARMA_POS)
        draw_text(surf, self.s.font, f"Upgrades: +HP {self.s.save.max_hp_up}  +DMG {self.s.save.dmg_up}", (6, 38), (200, 200, 215))

        self._relayout()
        for i, b in enumerate(self.btns):
            draw_button(surf, self.s.font, b, focused=(i == self.choice_idx))

        draw_text(surf, self.s.font, "Enter/Space: select   F11: fullscreen   F10: maximize", (6, VIRTUAL_H - 14), (170, 170, 190))


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


class SettingsState:
    PRESETS: list[tuple[int, int]] = [
        (640, 360),
        (960, 540),
        (1280, 720),
        (1600, 900),
        (1920, 1080),
    ]

    def __init__(self, shared: Shared) -> None:
        self.s = shared
        self.idx = 0
        self.custom_w = self.s.cfg.window_w
        self.custom_h = self.s.cfg.window_h
        self.focus = 0  # 0 preset, 1 w, 2 h, 3 apply/save, 4 back

    def handle_event(self, e: pg.event.Event) -> None:
        self.s.inp.handle_event(e)

    def update(self, dt: float) -> GameState | None:
        if self.s.inp.pressed(pg.K_ESCAPE):
            return KarmaHubState(self.s)

        if self.s.inp.pressed(pg.K_UP) or self.s.inp.pressed(pg.K_w):
            self.focus = (self.focus - 1) % 5
        if self.s.inp.pressed(pg.K_DOWN) or self.s.inp.pressed(pg.K_s):
            self.focus = (self.focus + 1) % 5

        if self.focus == 0:
            if self.s.inp.pressed(pg.K_LEFT) or self.s.inp.pressed(pg.K_a):
                self.idx = (self.idx - 1) % len(self.PRESETS)
            if self.s.inp.pressed(pg.K_RIGHT) or self.s.inp.pressed(pg.K_d):
                self.idx = (self.idx + 1) % len(self.PRESETS)
            if self.s.inp.pressed(pg.K_RETURN) or self.s.inp.pressed(pg.K_SPACE):
                self.custom_w, self.custom_h = self.PRESETS[self.idx]

        if self.focus in (1, 2):
            step = 40
            if self.s.inp.down(pg.K_LSHIFT) or self.s.inp.down(pg.K_RSHIFT):
                step = 10
            if self.s.inp.pressed(pg.K_LEFT) or self.s.inp.pressed(pg.K_a):
                if self.focus == 1:
                    self.custom_w = max(320, self.custom_w - step)
                else:
                    self.custom_h = max(180, self.custom_h - step)
            if self.s.inp.pressed(pg.K_RIGHT) or self.s.inp.pressed(pg.K_d):
                if self.focus == 1:
                    self.custom_w = min(3840, self.custom_w + step)
                else:
                    self.custom_h = min(2160, self.custom_h + step)

        if self.s.inp.pressed(pg.K_RETURN) or self.s.inp.pressed(pg.K_SPACE):
            if self.focus == 3:
                self.s.cfg.window_w = self.custom_w
                self.s.cfg.window_h = self.custom_h
                self.s.cfg.fullscreen = False
                self.s.cfg.save()
                self.s.window_request = WindowRequest(window_w=self.custom_w, window_h=self.custom_h, fullscreen=False)
            elif self.focus == 4:
                return KarmaHubState(self.s)

        return None

    def draw(self, surf: pg.Surface) -> None:
        surf.fill((12, 12, 18))
        draw_text(surf, self.s.font, "Settings (Resolution)", (6, 6))
        draw_text(surf, self.s.font, f"Current: {self.s.cfg.window_w}x{self.s.cfg.window_h}  Fullscreen: {self.s.cfg.fullscreen}", (6, 22), (200, 200, 215))

        y = 54
        p_w, p_h = self.PRESETS[self.idx]
        draw_text(surf, self.s.font, f"Preset: {p_w}x{p_h}  (Left/Right to change, Enter to copy)", (12, y), (235, 235, 245) if self.focus == 0 else (170, 170, 190))
        y += 20
        draw_text(surf, self.s.font, f"Custom Width:  {self.custom_w}  (Left/Right, Shift=smaller step)", (12, y), (235, 235, 245) if self.focus == 1 else (170, 170, 190))
        y += 20
        draw_text(surf, self.s.font, f"Custom Height: {self.custom_h}  (Left/Right, Shift=smaller step)", (12, y), (235, 235, 245) if self.focus == 2 else (170, 170, 190))
        y += 26
        draw_text(surf, self.s.font, "Apply + Save (resets fullscreen)", (12, y), (235, 235, 245) if self.focus == 3 else (170, 170, 190))
        y += 18
        draw_text(surf, self.s.font, "Back", (12, y), (235, 235, 245) if self.focus == 4 else (170, 170, 190))

        draw_text(surf, self.s.font, "Tip: Drag corners to resize. F11 fullscreen, F10 maximize.", (6, VIRTUAL_H - 14), (170, 170, 190))


