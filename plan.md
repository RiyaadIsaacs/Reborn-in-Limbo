# Reborn in Limbo - Plan (Day 1-3)

## High-Level Goal
Ship a playable Python/pygame 2D pixel-art roguelike loop where **memory fragments** are world pickups that the player chooses to collect, opening a dialogue choice overlay that modifies **karma**. Karma is spent between runs on permanent upgrades.

## MVP (Must function By End Of Day 2)
- A Limbo run starts and the player can move.
- A memory fragment pickup exists in the world and opens an overlay only when collected.
- Picking a choice adds respective karma.
- Combat exists (simple attack + enemy HP).
- Death ends the run and returns to the Karma Hub.
- Karma Hub allows spending karma on 2 permanent upgrades saved to disk through a json file (HP uses good karma; damage uses bad karma).
- New run applies upgrades.

## Day 1 - Setup And Planning
- Confirm MVP viability.
- Create project structure and baseline pygame window loop.
- Establish pixel-art scale factor and Github repository.

## Day 2 - Prototype Build
- Implement state machine (`LimboRun`, `MemoryOverlay`, `KarmaHub`).
- Implement player movement + simple combat.
- Implement memory fragment trigger + choice UI.
- Implement karma persistence + shop upgrades.
- Record Video 1 (2-5 min) showing loop + AI usage.

## Day 3 - Refinement
- Tune values and fix bugs.
- Add a final Boss Room at the end of a hallway with an entry lock and victory condition.
- Improve readability and visuals (UI, silhouettes, hit feedback).
- Record Video 2 (2-5 min) and finalize docs + reflections + ethics statement.

## AI Tools Used (Planned)
- Cursor (coding + debugging + doc maintenance)
- Cursor AI art generator (sprites/UI first-pass) + manual cleanup (palette/outline consistency)




