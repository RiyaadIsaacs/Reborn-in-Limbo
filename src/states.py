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
        self.karma_good_run: int = 0
        self.karma_bad_run: int = 0
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
        self._spawn_room_memory_pickups()

        # Special room circles
        self._room_special: dict[int, str] = {}  # room_idx -> "purify" | "corrupt"
        self._circle_used: set[int] = set()
        self._circle_fx: dict[int, float] = {}  # room_idx -> seconds remaining
        self._assign_special_rooms()

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
                            # Seal corridor edges: surround new floor with walls (only if empty).
                            for ny in (yy - 1, yy, yy + 1):
                                for nx in (xx - 1, xx, xx + 1):
                                    if 0 <= nx < self._grid_w and 0 <= ny < self._grid_h and self._tiles[ny][nx] == 0:
                                        self._tiles[ny][nx] = 2
            elif y0 == y1:
                x_start, x_end = (x0, x1) if x0 <= x1 else (x1, x0)
                for xx in range(x_start, x_end + 1):
                    for dy in range(-w + 1, w):
                        yy = y0 + dy
                        if 0 <= xx < self._grid_w and 0 <= yy < self._grid_h:
                            self._tiles[yy][xx] = 1
                            for ny in (yy - 1, yy, yy + 1):
                                for nx in (xx - 1, xx, xx + 1):
                                    if 0 <= nx < self._grid_w and 0 <= ny < self._grid_h and self._tiles[ny][nx] == 0:
                                        self._tiles[ny][nx] = 2

    def _spawn_room_enemies(self) -> None:
        # Spawn enemies based on room index; later rooms have more enemies.
        for ridx, room in enumerate(self.dungeon.rooms):
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
                self.enemies.append(Enemy(pos=pg.Vector2(gx * self._cell, gy * self._cell), hp=2, speed=22.0, room_idx=ridx))

    def _spawn_room_memory_pickups(self) -> None:
        # Memory pickups: add karma when collected (good/bad split based on pickup type).
        self.memory_pickups: list[tuple[pg.Vector2, int, int]] = []
        # tuple: (pos, room_idx, karma_sign) where karma_sign is +1 (good) or -1 (bad)
        for ridx, room in enumerate(self.dungeon.rooms):
            r = room.rect
            inner_x0 = r.x + 1
            inner_y0 = r.y + 1
            inner_x1 = r.x + r.w - 2
            inner_y1 = r.y + r.h - 2
            if inner_x1 <= inner_x0 or inner_y1 <= inner_y0:
                continue
            for _ in range(room.memory_count):
                gx = self.s.rng.randint(inner_x0, inner_x1)
                gy = self.s.rng.randint(inner_y0, inner_y1)
                sign = 1 if self.s.rng.random() < 0.7 else -1
                self.memory_pickups.append((pg.Vector2(gx * self._cell, gy * self._cell), ridx, sign))

    def _assign_special_rooms(self) -> None:
        # Choose up to 2 rooms as special (excluding start room).
        candidate = list(range(len(self.dungeon.rooms)))
        if 0 in candidate:
            candidate.remove(0)
        self.s.rng.shuffle(candidate)
        if candidate:
            self._room_special[candidate[0]] = "purify"
        if len(candidate) > 1:
            self._room_special[candidate[1]] = "corrupt"

    def _spawn_gatekeeper(self) -> None:
        # Spawn in the last room center.
        if self.dungeon.rooms:
            cx, cy = self.dungeon.rooms[-1].rect.center()
            pos = pg.Vector2(cx * self._cell, cy * self._cell)
        else:
            pos = pg.Vector2(self._world_w / 2, self._world_h / 2)
        self.enemies.append(Enemy(pos=pos, hp=6, speed=18.0, is_gatekeeper=True, radius=8, room_idx=max(0, len(self.dungeon.rooms) - 1)))
        self._gatekeeper_spawned = True

    def _room_index_at_grid(self, gx: int, gy: int) -> int:
        # Returns room index if inside its interior (not walls), else -1.
        for ridx, room in enumerate(self.dungeon.rooms):
            r = room.rect
            if (r.x + 1) <= gx <= (r.x + r.w - 2) and (r.y + 1) <= gy <= (r.y + r.h - 2):
                return ridx
        return -1

    def _is_walkable(self, gx: int, gy: int) -> bool:
        # Only floor is walkable. Empty and walls are solid.
        if gx < 0 or gy < 0 or gx >= self._grid_w or gy >= self._grid_h:
            return False
        return self._tiles[gy][gx] == 1

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
        # Prevent walking into non-walkable tiles.
        gx = int(self.player.pos.x) // self._cell
        gy = int(self.player.pos.y) // self._cell
        if not self._is_walkable(gx, gy):
            self.player.pos = old_pos

        # Enemy activation: only chase when player is inside enemy's room.
        player_room = self._room_index_at_grid(gx, gy)
        for en in self.enemies:
            if en.room_idx != player_room:
                continue
            d = self.player.pos - en.pos
            if d.length_squared() > 0.001:
                d = d.normalize()
            step = d * en.speed * dt
            # Axis-separated collision against dungeon tiles
            newx = pg.Vector2(en.pos.x + step.x, en.pos.y)
            gx2 = int(newx.x) // self._cell
            gy2 = int(newx.y) // self._cell
            if self._is_walkable(gx2, gy2):
                en.pos.x = newx.x
            newy = pg.Vector2(en.pos.x, en.pos.y + step.y)
            gx3 = int(newy.x) // self._cell
            gy3 = int(newy.y) // self._cell
            if self._is_walkable(gx3, gy3):
                en.pos.y = newy.y
        self.enemies = [e for e in self.enemies if e.hp > 0]

        # Collect memory pickups (karma gain)
        new_pickups: list[tuple[pg.Vector2, int, int]] = []
        for ppos, ridx, sign in self.memory_pickups:
            if (ppos - self.player.pos).length_squared() <= (self.player.radius + 4) ** 2:
                if sign > 0:
                    self.karma_good_run += 1
                else:
                    self.karma_bad_run += 1
            else:
                new_pickups.append((ppos, ridx, sign))
        self.memory_pickups = new_pickups

        # Special circle interaction (E)
        if player_room in self._room_special and player_room not in self._circle_used:
            if self.s.inp.pressed(pg.K_e):
                kind = self._room_special[player_room]
                if kind == "purify":
                    self.s.save.good_karma = max(0, self.s.save.good_karma - 10)
                else:
                    self.s.save.bad_karma = max(0, self.s.save.bad_karma - 10)
                self.s.save.save()
                self._circle_used.add(player_room)
                self._circle_fx[player_room] = 0.7

        # FX timers
        for k in list(self._circle_fx.keys()):
            self._circle_fx[k] -= dt
            if self._circle_fx[k] <= 0:
                del self._circle_fx[k]

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
            self.s.save.good_karma += self.karma_good_run
            self.s.save.bad_karma += self.karma_bad_run
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
            self.karma_good_run += 3
            self.s.save.good_karma += self.karma_good_run
            self.s.save.bad_karma += self.karma_bad_run
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

        # Draw memory pickups
        for ppos, ridx, sign in getattr(self, "memory_pickups", []):
            sx = int(ppos.x - self._cam.x)
            sy = int(ppos.y - self._cam.y)
            if sx < -10 or sy < -10 or sx > VIRTUAL_W + 10 or sy > VIRTUAL_H + 10:
                continue
            col = (250, 210, 90) if sign > 0 else (110, 150, 240)
            pg.draw.rect(surf, col, pg.Rect(sx - 2, sy - 2, 4, 4))

        # Draw special room circles
        player_gx = int(self.player.pos.x) // self._cell
        player_gy = int(self.player.pos.y) // self._cell
        player_room = self._room_index_at_grid(player_gx, player_gy)
        for ridx, kind in self._room_special.items():
            if ridx in self._circle_used:
                continue
            cx, cy = self.dungeon.rooms[ridx].rect.center()
            wx = cx * self._cell
            wy = cy * self._cell
            sx = int(wx - self._cam.x)
            sy = int(wy - self._cam.y)
            if sx < -40 or sy < -40 or sx > VIRTUAL_W + 40 or sy > VIRTUAL_H + 40:
                continue

            if kind == "purify":
                core = (255, 220, 110)
                glow = (255, 220, 110, 90)
                hover_text = "Hover_to_Purify (E)"
            else:
                core = (220, 80, 80)
                glow = (220, 80, 80, 90)
                hover_text = "Hover_to_Corrupt (E)"

            # Glow
            gsurf = pg.Surface((80, 80), pg.SRCALPHA)
            pg.draw.circle(gsurf, glow, (40, 40), 18)
            pg.draw.circle(gsurf, (glow[0], glow[1], glow[2], 40), (40, 40), 28)
            surf.blit(gsurf, (sx - 40, sy - 40))

            # Core ring
            pg.draw.circle(surf, core, (sx, sy), 14, width=2)
            pg.draw.circle(surf, core, (sx, sy), 8, width=1)

            # Hover UI only when player is in that room
            if player_room == ridx:
                draw_text(surf, self.s.font, hover_text, (sx - 40, sy - 28), (235, 235, 245))

        # Circle FX burst
        for ridx, t in self._circle_fx.items():
            cx, cy = self.dungeon.rooms[ridx].rect.center()
            wx = cx * self._cell
            wy = cy * self._cell
            sx = int(wx - self._cam.x)
            sy = int(wy - self._cam.y)
            p = max(0.0, min(1.0, 1.0 - t / 0.7))
            r = int(10 + p * 22)
            alpha = int(160 * (1.0 - p))
            fx = pg.Surface((r * 2 + 2, r * 2 + 2), pg.SRCALPHA)
            pg.draw.circle(fx, (255, 220, 140, alpha), (r + 1, r + 1), r, width=2)
            surf.blit(fx, (sx - r - 1, sy - r - 1))

        # HUD
        draw_text(surf, self.s.font, f"HP: {self.player.hp}/{self.player.stats.max_hp if self.player.stats else self.player.hp}", (6, 6), COL_TEXT)
        draw_text(surf, self.s.font, f"Good(run): {self.karma_good_run}  Bad(run): {self.karma_bad_run}", (6, 22), (210, 210, 225))
        draw_text(surf, self.s.font, f"Good(meta): {self.s.save.good_karma}  Bad(meta): {self.s.save.bad_karma}", (6, 36), (210, 210, 225))
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
            if choice.karma_delta >= 0:
                self.parent.karma_good_run += choice.karma_delta
            else:
                self.parent.karma_bad_run += abs(choice.karma_delta)
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
                if self.s.save.good_karma + self.s.save.bad_karma >= 5:
                    # Spend from good first.
                    spend = 5
                    take = min(self.s.save.good_karma, spend)
                    self.s.save.good_karma -= take
                    spend -= take
                    if spend > 0:
                        self.s.save.bad_karma = max(0, self.s.save.bad_karma - spend)
                    self.s.save.max_hp_up += 1
                    self.s.save.save()
            elif self.choice_idx == 1:
                if self.s.save.good_karma + self.s.save.bad_karma >= 5:
                    spend = 5
                    take = min(self.s.save.good_karma, spend)
                    self.s.save.good_karma -= take
                    spend -= take
                    if spend > 0:
                        self.s.save.bad_karma = max(0, self.s.save.bad_karma - spend)
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
        draw_text(surf, self.s.font, f"Good: {self.s.save.good_karma}  Bad: {self.s.save.bad_karma}", (6, 22), (210, 210, 225))
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


