from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class RectI:
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


@dataclass(frozen=True)
class Room:
    rect: RectI
    enemy_count: int
    memory_count: int
    is_boss_room: bool = False


@dataclass(frozen=True)
class Corridor:
    a: tuple[int, int]
    b: tuple[int, int]
    width: int
    # L-turn joint; must match the geometry used when stamping the corridor.
    mid: tuple[int, int]


@dataclass(frozen=True)
class Dungeon:
    rooms: list[Room]
    corridors: list[Corridor]


def _pick_side_point(r: RectI, side: str, rng: random.Random) -> tuple[int, int]:
    # Side point is guaranteed to be on one of the 4 sides (grid coords).
    if side == "N":
        return (rng.randint(r.x + 1, r.x2 - 2), r.y)
    if side == "S":
        return (rng.randint(r.x + 1, r.x2 - 2), r.y2 - 1)
    if side == "W":
        return (r.x, rng.randint(r.y + 1, r.y2 - 2))
    # "E"
    return (r.x2 - 1, rng.randint(r.y + 1, r.y2 - 2))


def _overlaps(a: RectI, b: RectI, pad: int = 1) -> bool:
    return not (
        a.x2 + pad <= b.x
        or b.x2 + pad <= a.x
        or a.y2 + pad <= b.y
        or b.y2 + pad <= a.y
    )


def generate_dungeon(
    *,
    rng: random.Random,
    grid_w: int,
    grid_h: int,
    room_count_min: int = 3,
    room_count_max: int = 5,
    room_w_range: tuple[int, int] = (6, 10),
    room_h_range: tuple[int, int] = (5, 8),
    corridor_width: int = 1,
    max_attempts: int = 200,
    enemies_base: int = 0,
    enemies_growth: int = 2,
    memories_base: int = 1,
    memories_growth: int = 1,
) -> Dungeon:
    # Narrative memories are placed in corridors / post-combat by the run state, not via room.memory_count.
    room_target = rng.randint(room_count_min, room_count_max)
    margin = 2
    placements: list[RectI] = []

    # Linear eastbound chain: play spaces are separated by real hallway gaps; boss is always last (far end).
    x = rng.randint(margin + 2, max(margin + 2, min(24, grid_w // 5)))
    y_ctr = rng.randint(
        margin + room_h_range[1] + 2,
        max(margin + room_h_range[1] + 3, grid_h - margin - room_h_range[1] - 2),
    )

    for i in range(room_target):
        is_last = i == room_target - 1
        rw = rng.randint(room_w_range[0], room_w_range[1])
        rh = rng.randint(room_h_range[0], room_h_range[1])
        if is_last:
            rw = min(rw + rng.randint(2, 5), grid_w - x - margin - 2)
            rh = min(rh + rng.randint(1, 4), grid_h - margin - 2)
        y = max(margin, min(grid_h - rh - margin, y_ctr - rh // 2 + rng.randint(-2, 2)))
        if x + rw >= grid_w - margin or y + rh >= grid_h - margin or rw < max(4, room_w_range[0] - 2):
            break
        placements.append(RectI(x, y, rw, rh))
        if is_last:
            break
        room_right = grid_w - margin - placements[-1].x2
        if room_right < room_w_range[0] + 8:
            break
        gap = rng.randint(8, min(18, room_right - room_w_range[0] - 2))
        x = placements[-1].x2 + gap

    # If the chain failed partway, use a scaled linear fallback (boss capstone on the right).
    if len(placements) < 3:
        slot = max(room_w_range[0], min(16, (grid_w - 24) // 3))
        gap_fb = max(8, min(16, grid_w // 20))
        x0 = margin + 2
        r0 = RectI(x0, grid_h // 2 - slot // 2 - 1, slot, min(room_h_range[1], slot + 2))
        r1 = RectI(r0.x2 + gap_fb, grid_h // 2 - slot // 2 - 1, slot, min(room_h_range[1], slot + 2))
        boss_w = min(slot + 4, max(room_w_range[0], grid_w - r1.x2 - gap_fb - margin - 2))
        boss_h = min(room_h_range[1] + 4, grid_h - margin * 2 - 4)
        r2 = RectI(r1.x2 + gap_fb, grid_h // 2 - boss_h // 2, boss_w, boss_h)
        placements = [r0, r1, r2]

    rooms = placements

    # Corridors: east exit -> west entrance when possible (straight hall); else L-turn between neighbors.
    corridors: list[Corridor] = []
    for i in range(1, len(rooms)):
        ra, rb = rooms[i - 1], rooms[i]
        y_lo = max(ra.y + 1, rb.y + 1)
        y_hi = min(ra.y2 - 2, rb.y2 - 2)
        if y_lo <= y_hi:
            y_align = rng.randint(y_lo, y_hi)
            a = (ra.x2 - 1, y_align)
            b = (rb.x, y_align)
        else:
            a = _pick_side_point(ra, "E", rng)
            b = _pick_side_point(rb, "W", rng)
        mid = (b[0], a[1]) if rng.random() < 0.5 else (a[0], b[1])
        corridors.append(Corridor(a=a, b=b, width=max(1, corridor_width), mid=mid))

    out_rooms: list[Room] = []
    last_idx = len(rooms) - 1
    for idx, r in enumerate(rooms):
        is_boss = idx == last_idx
        if is_boss:
            # Final room: boss arena only (no procedural spawns / pickups in generator).
            enemy_count = 0
            memory_count = 0
        else:
            enemy_count = max(0, enemies_base + idx * enemies_growth + rng.randint(0, 2))
            memory_count = 0
        out_rooms.append(
            Room(rect=r, enemy_count=enemy_count, memory_count=memory_count, is_boss_room=is_boss)
        )

    return Dungeon(rooms=out_rooms, corridors=corridors)

