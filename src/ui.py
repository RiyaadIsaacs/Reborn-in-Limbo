from __future__ import annotations

from dataclasses import dataclass
import pygame as pg

from .constants import COL_PANEL, COL_PANEL_BORDER, COL_TEXT, COL_TEXT_DIM


@dataclass
class Button:
    rect: pg.Rect
    label: str
    enabled: bool = True


def draw_panel(surf: pg.Surface, rect: pg.Rect) -> None:
    pg.draw.rect(surf, COL_PANEL, rect)
    pg.draw.rect(surf, COL_PANEL_BORDER, rect, width=2)


def draw_text(
    surf: pg.Surface,
    font: pg.font.Font,
    text: str,
    pos: tuple[int, int],
    color: tuple[int, int, int] = COL_TEXT,
) -> None:
    img = font.render(text, True, color)
    surf.blit(img, pos)


def draw_button(
    surf: pg.Surface,
    font: pg.font.Font,
    btn: Button,
    *,
    focused: bool = False,
) -> None:
    bg = (45, 45, 60) if btn.enabled else (30, 30, 40)
    border = (200, 200, 255) if focused else COL_PANEL_BORDER
    pg.draw.rect(surf, bg, btn.rect)
    pg.draw.rect(surf, border, btn.rect, width=2)
    label_col = COL_TEXT if btn.enabled else COL_TEXT_DIM
    img = font.render(btn.label, True, label_col)
    surf.blit(img, (btn.rect.x + 6, btn.rect.y + 6))

