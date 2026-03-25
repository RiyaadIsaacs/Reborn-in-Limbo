from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryChoice:
    label: str
    karma_delta: int


@dataclass(frozen=True)
class MemoryFragment:
    title: str
    body: str
    choices: tuple[MemoryChoice, ...]


FRAGMENTS: list[MemoryFragment] = [
    MemoryFragment(
        title="Flicker: The Apology",
        body="You remember a moment you could have owned your mistake. The memory waits.",
        choices=(
            MemoryChoice("Own_it (+2)", karma_delta=2),
            MemoryChoice("Dodge_it (-2)", karma_delta=-2),
        ),
    ),
    MemoryFragment(
        title="Flicker: The Promise",
        body="A promise you made. It echoes, asking what you meant by it.",
        choices=(
            MemoryChoice("Keep_it (+1)", karma_delta=1),
            MemoryChoice("Break_it (-1)", karma_delta=-1),
        ),
    ),
]

