from __future__ import annotations

import time
import pygame as pg

from .constants import FPS, SCALE, VIRTUAL_H, VIRTUAL_W
from .input_map import InputMap
from .save_data import SaveData
from .states import KarmaHubState, Shared


def main() -> None:
    pg.init()
    pg.display.set_caption("Reborn in Limbo (Prototype)")

    window = pg.display.set_mode((VIRTUAL_W * SCALE, VIRTUAL_H * SCALE))
    virtual = pg.Surface((VIRTUAL_W, VIRTUAL_H))
    clock = pg.time.Clock()

    inp = InputMap()
    save = SaveData.load()
    font = pg.font.SysFont("consolas", 12)
    rng = __import__("random").Random(int(time.time()))

    shared = Shared(inp=inp, save=save, font=font, rng=rng)
    state = KarmaHubState(shared)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        inp.begin_frame()

        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            else:
                state.handle_event(e)

        nxt = state.update(dt)
        if nxt is not None:
            state = nxt

        state.draw(virtual)
        pg.transform.scale(virtual, window.get_size(), window)
        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()

