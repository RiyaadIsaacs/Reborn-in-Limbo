from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame as pg


@dataclass(frozen=True)
class Job:
    src: Path
    dst: Path
    out_w: int | None
    out_h: int | None


def _is_bg_pixel(c: pg.Color, a: int, b: int, tol: int) -> bool:
    return abs(c.r - a) <= tol and abs(c.g - a) <= tol and abs(c.b - a) <= tol or (
        abs(c.r - b) <= tol and abs(c.g - b) <= tol and abs(c.b - b) <= tol
    )


def _infer_checker_grays(img: pg.Surface) -> tuple[int, int]:
    # Background is a 2-color checkerboard (grays). Sample corners to guess both values.
    pts = [(0, 0), (img.get_width() - 1, 0), (0, img.get_height() - 1), (img.get_width() - 1, img.get_height() - 1)]
    vals: list[int] = []
    for x, y in pts:
        c = img.get_at((x, y))
        vals.append(int((c.r + c.g + c.b) / 3))
    vals = sorted(set(vals))
    if len(vals) == 1:
        v = vals[0]
        return max(0, v - 40), min(255, v + 40)
    return vals[0], vals[-1]


def _remove_checker_to_alpha(img: pg.Surface, *, tol: int = 10) -> pg.Surface:
    src = img.convert_alpha()
    a, b = _infer_checker_grays(src)
    w, h = src.get_size()
    for y in range(h):
        for x in range(w):
            c = src.get_at((x, y))
            if _is_bg_pixel(c, a, b, tol):
                src.set_at((x, y), pg.Color(0, 0, 0, 0))
    return src


def _tight_bbox_alpha(img: pg.Surface, *, alpha_min: int = 1) -> pg.Rect | None:
    w, h = img.get_size()
    minx, miny = w, h
    maxx, maxy = -1, -1
    for y in range(h):
        for x in range(w):
            if img.get_at((x, y)).a >= alpha_min:
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    if maxx < minx or maxy < miny:
        return None
    return pg.Rect(minx, miny, (maxx - minx + 1), (maxy - miny + 1))


def _resize_nearest(img: pg.Surface, size: tuple[int, int]) -> pg.Surface:
    # pygame's scale is nearest-neighbor (good for crisp pixels).
    return pg.transform.scale(img, size)


def process(job: Job) -> None:
    img = pg.image.load(str(job.src))
    img = _remove_checker_to_alpha(img, tol=12)

    bbox = _tight_bbox_alpha(img, alpha_min=2)
    if bbox is None:
        w = int(job.out_w or img.get_width())
        h = int(job.out_h or img.get_height())
        out = pg.Surface((w, h), pg.SRCALPHA)
        pg.image.save(out, str(job.dst))
        return

    cropped = img.subsurface(bbox).copy()

    # If no target size is provided, keep full detail: output the tight-cropped sprite as-is.
    if job.out_w is None or job.out_h is None:
        out = cropped
    else:
        # Scale down/up to fit in the target while preserving aspect, then center.
        cw, ch = cropped.get_size()
        scale = min(job.out_w / max(1, cw), job.out_h / max(1, ch))
        nw = max(1, int(round(cw * scale)))
        nh = max(1, int(round(ch * scale)))
        scaled = _resize_nearest(cropped, (nw, nh))

        out = pg.Surface((job.out_w, job.out_h), pg.SRCALPHA)
        out.blit(scaled, (job.out_w // 2 - nw // 2, job.out_h // 2 - nh // 2))
    job.dst.parent.mkdir(parents=True, exist_ok=True)
    pg.image.save(out, str(job.dst))


def main() -> None:
    pg.init()
    # Needed for convert()/convert_alpha() on some platforms.
    try:
        pg.display.set_mode((1, 1), flags=getattr(pg, "HIDDEN", 0))
    except Exception:
        pg.display.set_mode((1, 1))
    root = Path(__file__).resolve().parent.parent
    assets = root / "assets"

    jobs = [
        # Default: preserve detail (crop + transparent), let the game scale at runtime.
        Job(src=assets / "player.png", dst=assets / "player.png", out_w=None, out_h=None),
        Job(src=assets / "enemy.png", dst=assets / "enemy.png", out_w=None, out_h=None),
        Job(src=assets / "boss.png", dst=assets / "boss.png", out_w=None, out_h=None),
    ]

    for j in jobs:
        process(j)

    pg.quit()


if __name__ == "__main__":
    main()

