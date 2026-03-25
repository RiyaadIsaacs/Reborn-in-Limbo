from __future__ import annotations

import time
import pygame as pg

from .constants import FPS, MIN_SCALE, VIRTUAL_H, VIRTUAL_W
from .config import AppConfig
from .input_map import InputMap
from .save_data import SaveData
from .states import KarmaHubState, Shared


def _compute_scale(window_size: tuple[int, int]) -> int:
    w, h = window_size
    return max(MIN_SCALE, min(w // VIRTUAL_W, h // VIRTUAL_H))


def _blit_scaled(virtual: pg.Surface, window: pg.Surface) -> None:
    ww, wh = window.get_size()
    scale = _compute_scale((ww, wh))
    sw, sh = VIRTUAL_W * scale, VIRTUAL_H * scale
    x = (ww - sw) // 2
    y = (wh - sh) // 2
    window.fill((0, 0, 0))
    pg.transform.scale(virtual, (sw, sh), window.subsurface(pg.Rect(x, y, sw, sh)))


def _set_window(cfg: AppConfig) -> pg.Surface:
    flags = pg.RESIZABLE
    if cfg.fullscreen:
        flags |= pg.FULLSCREEN
        return pg.display.set_mode((0, 0), flags)
    return pg.display.set_mode((cfg.window_w, cfg.window_h), flags)


def main() -> None:
    pg.init()
    pg.display.set_caption("Reborn in Limbo (Prototype)")

    cfg = AppConfig.load()
    window = _set_window(cfg)
    virtual = pg.Surface((VIRTUAL_W, VIRTUAL_H))
    clock = pg.time.Clock()

    inp = InputMap()
    save = SaveData.load()
    font = pg.font.SysFont("consolas", 12)
    rng = __import__("random").Random(int(time.time()))

    shared = Shared(inp=inp, save=save, font=font, rng=rng, cfg=cfg, window_request=None)
    state = KarmaHubState(shared)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        inp.begin_frame()

        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            elif e.type == pg.VIDEORESIZE:
                # Corner-drag resize
                cfg.window_w, cfg.window_h = e.w, e.h
                if not cfg.fullscreen:
                    cfg.save()
                window = _set_window(cfg)
            else:
                # Global shortcuts:
                # F11 toggles fullscreen, F10 maximizes to desktop, Ctrl+0 resets to default.
                if e.type == pg.KEYDOWN:
                    if e.key == pg.K_F11:
                        cfg.fullscreen = not cfg.fullscreen
                        cfg.save()
                        window = _set_window(cfg)
                    elif e.key == pg.K_F10:
                        # Maximize (borderless-ish) by setting to desktop size.
                        try:
                            dw, dh = pg.display.get_desktop_sizes()[0]
                        except Exception:
                            dw, dh = 1280, 720
                        cfg.fullscreen = False
                        cfg.window_w, cfg.window_h = dw, dh
                        cfg.save()
                        window = _set_window(cfg)
                    elif e.key == pg.K_0 and (e.mod & pg.KMOD_CTRL):
                        cfg.fullscreen = False
                        cfg.window_w, cfg.window_h = 960, 540
                        cfg.save()
                        window = _set_window(cfg)
                state.handle_event(e)

        nxt = state.update(dt)
        if nxt is not None:
            state = nxt

        if shared.window_request is not None:
            req = shared.window_request
            shared.window_request = None
            cfg.window_w = req.window_w
            cfg.window_h = req.window_h
            cfg.fullscreen = req.fullscreen
            cfg.save()
            window = _set_window(cfg)

        state.draw(virtual)
        _blit_scaled(virtual, window)
        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()

