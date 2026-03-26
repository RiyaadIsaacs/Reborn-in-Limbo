# Reborn in Limbo (Prototype)

AI-assisted 2D pixel-art roguelike prototype.

## Status
Playable jam prototype: hub → run → corridor memory pickups → combat rooms → final boss room.

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
- **Pause menu (in run)**: Esc
- **Fullscreen**: F11
- **Maximize**: F10

## Current gameplay notes (polished build)
- **Memory fragments**: appear as pickups (mostly in corridors). Dialogue opens only when collected.
- **Final boss room**: last room in the chain; entry locks until the boss is defeated.
- **Circles / power-ups**:
  - **Gold circle**: press **E** to spend **3 Good(run) karma** → gain **+1 GoldAmmo**
  - **Red circle**: press **E** to spend **3 Bad(run) karma** → gain **+2 RedAmmo**
- **Ammo UI**: RedAmmo/GoldAmmo are shown on the in-run HUD and reset on death.
- **Pause menu**: Esc opens Resume / Settings / Return to Hub.
- **Settings -> Controls**: dedicated controls reference screen.
- **Hub menu**: includes an **Exit_Game** option.


## Reflections

Where AI excelled:
AI did well with making basic classes and building blocks for each class so that I could alter classes for my specfic needs. Cursor was strongest when I had a clear prompt that was set up for making: state-machine changes, UI text adjustments, room generation logic, and looking through other coding tasks, were completed in a much faster fashion than if done solo. It also helped maintain the github repository really well. 

Where it misled me: 
Cursor made assumptions about some design choices and those had to be manually edited (intrusive automated dialogue on a random timer and visual processing in image gen that had artifacting). Some generated things were blurry or unreadable and required some photoshop work. AI also occasionally produced implementation like it designed the attack feature without considering the visual aspect for the player to see their attack range.

How AI altered the creative process:
AI shifted my workflow from "build and see if an idea works" to "Rapid prototype a mechanic and see if it fits."This cut down obvious long drawn out design choices allowing for clean and quick finalization of what the final MVP would be. This worked out best with the connected systems like spawning rules, combat input mapping, and state transitions for the enemy AI's.

Ethical considerations:
My approach was to treat Cursor as a junior that can be told specific instructions while I make the final design choices. Originality was kept up by making changes to code in the project; places where the AI would consistetnly misinterpret the idea I tried to communicate. The overall design choices such as the core loop structure and final feature acceptance were my decisions as well. Cursor AI did provide drafts and alternatives that were worth considering but did not fit the overall idea the game needed to be. Transparency is addressed through the refinement log that cursor managed and documented the AI involvement in code and content.



