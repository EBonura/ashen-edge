# Ashen Edge — Design Document

## Overview
A PICO-8 action-platformer. The player controls **Aletha**, a neutral-toned figure navigating a world consumed by red corruption. The core loop is combat, exploration, and dismantling the boss's power by extinguishing corrupted torches.

## Visual Language
- **Red** = corruption, the boss's influence (torches, enemies, damage)
- **Neutral/gray** = Aletha, uncorrupted, natural
- **Black** = the world, ash, emptiness
- Torches glow red when lit (corrupted), go dark/gray when extinguished (freed)
- Portals shift to red when active (checkpoints reclaimed)

## Player — Aletha
- Platforming: run, jump
- Two-hit combo: slash → cross-slice
- Can destroy certain tiles by attacking (breakable walls/floors)
- Invincibility frames after taking damage
- HP bar (HUD, top-left), gems counter below

## Enemies

### Spiders (type 3)
- Basic ground enemy
- Has HP, can be killed

### Wheelbots (type 4)
- Patrol behavior, sleep state
- Forward dash attack
- Has HP, invincibility during dash

### Hellbots (type 5)
- Tougher enemy
- Has HP

### Boss
- Final encounter
- Power tied to corrupted torches (more extinguished = weaker)
- Separate sprite system with multi-part animations

## Entities

### Switches (type 2)
- Toggled by attacking
- Cooldown after activation
- Purpose: open paths, activate platforms (?)

### Portals (type 6)
- Checkpoints — activate by walking near
- Visual shift to red when active
- Respawn point on death

### Torches (type 7)
- Start **lit** (red, animated, 6-frame cycle)
- Extinguished by attacking → static gray frame
- Extended hitbox (8px margin) for forgiving interaction
- Core mechanic: each extinguished torch weakens the final boss
- Scattered throughout levels as optional/exploration objectives

### Zones (type 8)
- Invisible trigger tiles
- Display text when player stands on them
- Used for tutorials, narration, lore

## Game Flow
1. **Title screen** → "press x" → fade to gameplay
2. **Gameplay** — explore, fight, extinguish torches, find checkpoints
3. **Death** → "you died" screen → respawn at last checkpoint
4. **Boss** — difficulty scales with how many torches remain lit

## Level Structure
- Parallax background layer (memcpy-blitted tiles)
- Main gameplay layer (sprite tiles, flippable)
- Entities placed via level_data.json
- Multi-group level system

## Open Questions
- [ ] What is the world? Why is it ashen?
- [ ] Who is Aletha? Why is she here?
- [ ] What is the boss? What is the corruption?
- [ ] What do gems do? Currency? Score? Lore significance?
- [ ] What do switches control?
- [ ] How exactly does torch count affect the boss fight?
- [ ] Is there an ending? Multiple endings based on torch count?
- [ ] Are there multiple levels/areas or one continuous map?
- ~~What are the zone texts?~~ → Aletha's inner thoughts, reacting to her surroundings
