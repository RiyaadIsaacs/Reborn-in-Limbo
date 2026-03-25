# Reborn in Limbo - Plan (Day 1-3)

## High-Level Goal
Ship a playable Python/pygame 2D pixel-art roguelike loop where **memory fragments** appear during Limbo runs as dialogue choices that modify **karma**. Karma is spent between runs on permanent upgrades and optional run items.

## MVP (Must Work By End Of Day 2)
- A Limbo run starts and the player can move.
- A memory fragment overlay appears at least once per run and offers 2 choices.
- Picking a choice changes karma.
- Combat exists (simple attack + enemy HP).
- Death ends the run (permadeath) and returns to the Karma Hub.
- Karma Hub allows spending karma on 2 permanent upgrades saved to disk.
- New run applies upgrades.

## Day 1 - Setup And Planning
- Confirm MVP boundaries in `mvp.md`.
- Create project structure and baseline pygame window loop.
- Draft at least 2 memory fragments (text + choices + karma values).
- Establish pixel-art scale factor and placeholder sprites.

## Day 2 - Prototype Build
- Implement state machine (`LimboRun`, `MemoryOverlay`, `KarmaHub`).
- Implement player movement + simple combat.
- Implement memory fragment trigger + choice UI.
- Implement karma persistence + shop upgrades.
- Record Video 1 (2-5 min) showing loop + AI usage.

## Day 3 - Refinement
- Tune values and fix bugs.
- Add a Gatekeeper (boss placeholder) and victory condition (break curse).
- Improve readability (UI, silhouettes, hit feedback).
- Record Video 2 (2-5 min) and finalize docs + reflections + ethics statement.

## AI Tools Used (Planned)
- Cursor (coding + debugging + doc maintenance)
- AI art generator (sprites/UI first-pass) + manual cleanup (palette/outline consistency)
- Optional: AI sound/music generator

## Reflection Prompts (To Fill In Later)
Add ~200 words each:
- Where did AI excel, and where did it mislead or limit you?
- How did AI alter your creative or technical process?
- What would you change about your collaboration with AI next time?
- Ethics: originality, transparency, fair use, and crediting.

