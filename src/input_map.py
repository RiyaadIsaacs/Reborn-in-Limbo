from __future__ import annotations

import pygame as pg


class InputMap:
    def __init__(self) -> None:
        self._pressed: set[int] = set()
        self._just_pressed: set[int] = set()

    def begin_frame(self) -> None:
        self._just_pressed.clear()

    def handle_event(self, e: pg.event.Event) -> None:
        if e.type == pg.KEYDOWN:
            self._pressed.add(e.key)
            self._just_pressed.add(e.key)
        elif e.type == pg.KEYUP:
            self._pressed.discard(e.key)

    def down(self, key: int) -> bool:
        return key in self._pressed

    def pressed(self, key: int) -> bool:
        return key in self._just_pressed

