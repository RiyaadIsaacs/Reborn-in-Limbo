# MVP (3-Day Vertical Slice)

## Prototype Focus
This prototype demonstrates AI-assisted development of a **roguelike loop** with **memory-fragment dialogue choices**.

## MVP Requirements
1. Start Limbo run.
2. Player can move and fight enemies (simple combat).
3. Memory fragments exist as pickups in the world; dialogue overlay opens only when collected.
4. Each choice grants **karma** (prototype scope: karma-only effects).
5. The final room is a dedicated **Boss Room** at the end of a hallway (no standard enemies spawn inside it).
6. Entering the Boss Room locks the entrance until the boss is defeated (victory).
7. If the player dies (permadeath), the run ends and the player returns to a **Karma Hub**.
8. In the Karma Hub, the player can spend karma on 2 permanent upgrades (saved to disk): MaxHP uses good karma; damage uses bad karma.
9. Restarting starts a new run with upgraded stats.

## Explicit Out Of Scope
- Deep branching story trees.
- Complex inventory systems.
- Many enemy archetypes.
- Cinematic scenes or cutscenes.

