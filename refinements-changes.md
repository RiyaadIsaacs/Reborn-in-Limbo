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

**2026-03-26**
- Goal: Make story beats player-controlled and corridor-paced.
- Prompt (summary): Refactor Memory logic so dialogue never opens automatically; spawn memories mainly in hallways; if a memory is in a room, hide it until that room is cleared.
- AI output (summary): Removed timer-based fragment triggers; created world `MemoryPickup` objects; corridor-first placement; room-locked reveal after enemies in that room are defeated.
- What I changed manually: Verified the new flow doesn’t pop dialogue unless the player collides with an active pickup.
- Result / test: No random/timer dialogue; memories act as breathers between fights.
- Decision / scope note: Story beats should be intentional, not interruptions.

**2026-03-26**
- Goal: Add a dedicated final boss room.
- Prompt (summary): Ensure the last room is boss-only; lock the entrance on player entry; spawn/wake boss only after lock; unlock on boss defeat; exclude procedural spawns from boss room.
- AI output (summary): Marked last room as boss arena; excluded spawners from boss area; implemented corridor gate lock/unlock and boss spawn after entry.
- What I changed manually: Tuned the generator so rooms form an eastbound chain and the boss room is always at the end of a hallway.
- Result / test: Boss room is consistently the final room and the lock/victory sequence works.
- Decision / scope note: One boss, one clear end goal per run.

**2026-03-26**
- Goal: Make upgrades spend the correct karma type.
- Prompt (summary): Require good karma for MaxHP upgrades and bad karma for Damage upgrades.
- AI output (summary): Hub upgrade costs were split by karma type and labels updated.
- What I changed manually: N/A
- Result / test: HP can’t be bought with bad karma and damage can’t be bought with good karma.
- Decision / scope note: Tie progression to moral axis for clarity.

**2026-03-26**
- Goal: Polish combat pacing and add run power-ups.
- Prompt (summary): Remove meta karma UI from run HUD; make circles persistent; spend 3 run karma to gain ammo; add red-orb projectile (left click) and gold damage ring (Q); increase melee range with a visible indicator; reset ammo/effects on death.
- AI output (summary): Added mouse input + virtual mouse mapping; run-only ammo counters; projectile + ring effects; simplified circle prompts; removed meta-karma HUD line.
- What I changed manually: Verified controls and that ammo resets on death.
- Result / test: Circles act as optional breather power-ups; combat readability improved with range indicator and ammo UI.
- Decision / scope note: Keep power-ups simple, readable, and run-scoped.

