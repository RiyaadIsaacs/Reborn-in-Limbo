# Reborn in Limbo (Prototype)

AI-assisted 2D pixel-art roguelike prototype. Memory fragments are physical pickups (mostly in corridors) that open a dialogue choice overlay only when collected. Karma is spent between runs on permanent upgrades.

## Status
Playable jam prototype: hub → run → corridor memory pickups → combat rooms → locked final boss room.

## Run
1. Install Python 3.11+
2. Install deps: `pip install -r requirements.txt`
3. Run: `python -m src.main`

## Controls
- **Move**: WASD / Arrow keys
- **Attack**: Space
- **Interact (special circles / power-ups)**: E
- **Shoot red orb (costs RedAmmo)**: Left Click
- **Activate gold ring (costs GoldAmmo)**: Q
- **Fullscreen**: F11
- **Maximize**: F10

## Current gameplay notes (polished build)
- **Memory fragments**: appear as pickups (mostly in corridors). Dialogue opens only when collected.
- **Final boss room**: last room in the chain; entry locks until the boss is defeated.
- **Circles / power-ups**:
  - **Gold circle**: press **E** to spend **3 Good(run) karma** → gain **+1 GoldAmmo**
  - **Red circle**: press **E** to spend **3 Bad(run) karma** → gain **+2 RedAmmo**
  - Circles **do not disappear** after use.
- **Ammo UI**: RedAmmo/GoldAmmo are shown on the in-run HUD and reset on death.

## AI usage (will be expanded)
- Code: Cursor (AI-assisted IDE)
- Art: AI tools + manual pixel clean-up

## Recording Videos (Day 2 and Day 3)
- Record 2–5 minutes showing:
  - Karma Hub -> start run -> collect a memory pickup (dialogue opens) -> combat -> enter boss room (locks) -> defeat boss -> victory -> back to hub
  - Explain which parts were AI-generated and what you changed by hand
- Tools: OBS Studio, Xbox Game Bar, or any screen recorder.

## AI Ethics Statement (Draft)
This project uses AI tools to assist with code and asset creation. All AI-generated outputs are reviewed, tested, and modified where needed. Any AI-generated art, audio, or text will be credited (tool name + what was generated) and will not include restricted or offensive content. Where external assets are used, licenses and sources will be documented to support fair use and originality requirements.

## Reflections (To Fill In)
Write ~200 words each:
- Where did AI excel, and where did it mislead or limit you?
- How did AI alter your creative or technical process?
- What would you change about your collaboration with AI next time?
- Ethical considerations: originality, transparency, fair use, and crediting.

