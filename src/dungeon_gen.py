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


@dataclass(frozen=True)
class Corridor:
    a: tuple[int, int]
    b: tuple[int, int]
    width: int


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
    room_target = rng.randint(room_count_min, room_count_max)
    rooms: list[RectI] = []

    # Place non-overlapping rooms.
    attempts = 0
    while len(rooms) < room_target and attempts < max_attempts:
        attempts += 1
        rw = rng.randint(room_w_range[0], room_w_range[1])
        rh = rng.randint(room_h_range[0], room_h_range[1])
        x = rng.randint(1, max(1, grid_w - rw - 1))
        y = rng.randint(1, max(1, grid_h - rh - 1))
        cand = RectI(x, y, rw, rh)
        if any(_overlaps(cand, ex, pad=1) for ex in rooms):
            continue
        rooms.append(cand)

    # If we couldn't place enough, just use what we have (but ensure at least 3).
    if len(rooms) < 3:
        # Force 3 small rooms in a simple chain layout.
        rooms = [
            RectI(2, 2, 7, 6),
            RectI(grid_w // 2 - 3, 2, 7, 6),
            RectI(grid_w // 2 - 3, grid_h // 2, 7, 6),
        ]

    # Connect rooms into a chain so each attaches to a side of its neighbor.
    corridors: list[Corridor] = []
    sides = ["N", "S", "E", "W"]
    for i in range(1, len(rooms)):
        ra = rooms[i - 1]
        rb = rooms[i]
        sa = rng.choice(sides)
        sb = rng.choice(sides)
        a = _pick_side_point(ra, sa, rng)
        b = _pick_side_point(rb, sb, rng)
        corridors.append(Corridor(a=a, b=b, width=max(1, corridor_width)))

    out_rooms: list[Room] = []
    for idx, r in enumerate(rooms):
        enemy_count = max(0, enemies_base + idx * enemies_growth + rng.randint(0, 2))
        memory_count = max(0, memories_base + idx * memories_growth + rng.randint(0, 1))
        out_rooms.append(Room(rect=r, enemy_count=enemy_count, memory_count=memory_count))

    return Dungeon(rooms=out_rooms, corridors=corridors)

