# Refinements / Changes Log

This is a running log of AI-assisted iteration and scope decisions. Keep entries short and dated.

## Template
**Date/Time:**
- Goal:
- Prompt (summary):
- AI output (summary):
- What I changed manually:
- Result / test:
- Decision / scope note:

## Entries
**2026-03-25**
- Goal: Initialize repo + lock MVP vertical slice.
- Prompt (summary): Set up a minimal repo and define an MVP for a memory-fragment roguelike loop.
- AI output (summary): Created baseline docs and MVP spec.
- What I changed manually: Confirmed project root and adjusted plan direction to Python/pygame.
- Result / test: Repo clean; pygame available.
- Decision / scope note: Memory fragments during Limbo runs; prototype choices affect karma only.

**2026-03-25**
- Goal: Implement a playable MVP loop in pygame.
- Prompt (summary): Create a simple state machine (hub/run/memory overlay), movement, basic combat, karma persistence, and a gatekeeper victory.
- AI output (summary): Added `src/` with pygame window loop, `LimboRunState`, `MemoryOverlayState`, `KarmaHubState`, JSON save, and two sample memory fragments.
- What I changed manually: Verified correct project folder (`Cursor Projects`) and ensured the prototype runs via `python -m src.main`.
- Result / test: Prototype window opens; hub -> run -> memory overlay -> death/hub loop works at a basic level.
- Decision / scope note: Keep choices karma-only for now; expand memory text and add more fragments after stability.

