# Background Image Generation Prompts

## Purpose

This file is the generation plan for default scene backgrounds.

These images are base fallbacks. Later we can generate or render anchor influence overlays on top of them: frost/stasis, entropy/ash, gravity/storm, evolution/bio-growth. Base images should stay clean enough to work without overlays.

Do not use modern post-apocalyptic or shooter references. The world is ancient survival fantasy in the collapsed remains of a lost monolithic civilization.

## Current Data Facts

Exploration already has exact location backgrounds through `WorldNavigationDTO.background_url`.

D4 city/hub already has many exact static images under:

```text
src/frontend/static/images/exploration/city/d4/
```

Combat and arena should not invent their own unrelated background locally. They should receive a resolved scene context.

The important runtime priority is:

```text
exact location background_url
-> terrain_type / node type fallback
-> biome_id fallback
-> future anchor overlay variant
-> global fallback
```

For D4, `biome_id=city_ruins` is not enough. D4 is the old capital: roads, gates, wall walks, broken districts, paved hub areas, foundations, shrines, markets, and collapsed quarters are different node types inside the same city-ruins biome.

## Known D4 Terrain Types

These are already present in world generation/static loading:

- `ancient_pavement`
- `ruin_road_main`
- `city_ruins`
- `ruined_foundation`
- `city_gate_outer`
- `outer_monolith_wall_walk`

Useful D4 tags from static locations include:

- `hub_center`
- `gate`
- `ruins`
- `street`
- `inner_wall`
- `bastion`
- `market`
- `tavern`
- `forge`
- `chapel`
- `warehouse`
- `guardhouse`
- `armory`
- `ancient_tower`
- `magic_pocket`
- `monolith`
- `overgrowth`

## Known Biomes

Open-world biome fallbacks currently needed:

- `city_ruins`
- `mountains`
- `forest`
- `hills`
- `grassland`
- `meadow`
- `badlands`
- `canyon`
- `savanna`
- `swamp`
- `marsh`
- `highlands`
- `jungle`
- `wasteland`

## Global Style Prompt

Append this style block to every prompt unless a specific prompt says otherwise:

```text
dark survival fantasy environment, ruins of a lost monolithic civilization, ancient black and white monolith stone, faint ether-gold veins embedded in architecture, no modern technology, no guns, no cars, no concrete apartment blocks, no asphalt, no power lines, no sci-fi panels, no text, no logo, no characters, no monsters, no foreground weapon, wide 16:9 landscape, usable as an MMORPG combat and exploration UI background, readable center area for dialogue and combat UI, darker side edges for interface panels, cinematic depth, detailed but not cluttered, dark but not pure black, painterly realistic game concept art
```

Negative prompt:

```text
modern city, soviet ruins, firearms, gas mask, cars, trucks, cables, neon cyberpunk, futuristic screens, soldiers, people, monsters, letters, watermark, logo, UI, pure black void, blurry low detail, cartoon, anime
```

## Batch Rules

Generate in batches of 12 images because of generation limits.

Recommended order:

1. Batch 01: D4 old-capital terrain/node fallbacks.
2. Batch 02: open-world biome fallbacks.
3. Batch 03: arena, scenario, and remaining system fallbacks.

Use stable filenames. The exact generated image can later be moved or converted to `.webp`.

## Batch 01 - D4 Old Capital Node Fallbacks

### 01 ancient_pavement_hub

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/ancient_pavement_hub_01.webp
```

Prompt:

```text
protected inner district of the old capital, broad ancient pavement made from pale monolith slabs, broken but still clean enough to feel safe, low tents and scavenged wooden repairs kept small at the edges, distant portal shield glow above a central plaza, monumental black and white stone arches, faint ether-gold veins in the ground
```

### 02 ruin_road_main

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/ruin_road_main_01.webp
```

Prompt:

```text
main ruined road of the old capital, wide cracked monolith avenue leading from the protected hub toward distant sealed gates, collapsed buildings on both sides, fallen statues, broken road markers, dust in the air, center lane open and readable
```

### 03 city_ruins_collapsed_district

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/city_ruins_collapsed_district_01.webp
```

Prompt:

```text
collapsed district of a former ancient capital, no clear road, piled stone floors, broken facades, half-buried courtyards, shattered monolith columns, old city layers fallen into each other, navigable combat space in the center
```

### 04 ruined_foundation

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/ruined_foundation_01.webp
```

Prompt:

```text
ruined building foundation in the old capital, exposed rectangular floor plan, broken threshold stones, collapsed walls around waist height, scattered ancient masonry, basement opening in shadow, clear flat center for combat
```

### 05 city_gate_outer

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/city_gate_outer_01.webp
```

Prompt:

```text
sealed outer gate of D4 old capital, enormous monolith gate doors locked by ancient mechanisms, road ending at the gate, high wall on both sides, weathered gatehouse ruins, faint shield residue in the air, no modern elements
```

### 06 outer_monolith_wall_walk

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/outer_monolith_wall_walk_01.webp
```

Prompt:

```text
wide walkway on top of the outer monolith wall around the old capital, one side shows ruined city rooftops below, the other side drops into mist beyond the barrier, massive black and white stone blocks, ancient parapets, clear combat path
```

### 07 inner_wall_bastion

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/inner_wall_bastion_01.webp
```

Prompt:

```text
damaged inner bastion inside the old capital, defensive wall corner, broken watch platforms, stacked monolith blocks, old barricades made from scavenged wood, city ruins visible beyond, center space open for a fight
```

### 08 market_ruins

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/market_ruins_01.webp
```

Prompt:

```text
abandoned market square inside the old capital, broken stone stalls, torn fabric awnings, barter tables repaired from salvaged wood, ancient paved plaza beneath debris, ruined facades around the square, no people, no modern goods
```

### 09 tavern_refuge_exterior

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/tavern_refuge_exterior_01.webp
```

Prompt:

```text
last refuge tavern built into a ruined monolith structure, warm dim light behind repaired shutters, patched wooden additions against ancient stone, safe but poor settlement feeling, empty street in front, old capital ruins around it
```

### 10 broken_shrine

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/broken_shrine_01.webp
```

Prompt:

```text
broken shrine in the old capital, cracked circular altar, fallen monolith idols, faint ether residue in engraved channels, collapsed chapel roof open to dark sky, scattered rubble, no religious text or symbols, clear center area
```

### 11 ancient_forge

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/ancient_forge_01.webp
```

Prompt:

```text
ancient forge quarter of the old capital, cold massive furnaces built from black monolith stone, broken anvils, dormant ether-gold channels, collapsed workshop arches, soot and dust, no modern machinery, center floor open
```

### 12 shadow_quarter

Target path:

```text
src/frontend/static/images/game/backgrounds/terrain/shadow_quarter_01.webp
```

Prompt:

```text
shadowed ruined quarter of the old capital, narrow broken street, leaning monolith facades, deep doorways, scattered debris, subtle cold ether glow from cracks, oppressive but readable, no modern alley elements, center path clear
```

## Batch 02 - Open World Biome Fallbacks

### 01 forest

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/forest_01.webp
```

Prompt:

```text
ancient forest reclaiming fragments of monolith road, huge roots crossing old stone, broken white-black columns swallowed by moss, dim filtered light, no modern forest trail, clear clearing in the center
```

### 02 meadow

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/meadow_01.webp
```

Prompt:

```text
wild meadow around fallen ancient stones, pale grass and flowers growing through cracked monolith slabs, distant old capital wall fragments on the horizon, quiet unsafe beauty, clear open center
```

### 03 grassland

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/grassland_01.webp
```

Prompt:

```text
open grassland crossed by remnants of an ancient monolith road, tall windblown grass, scattered broken markers, distant ruins barely visible, wide sky, readable combat ground in the center
```

### 04 hills

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/hills_01.webp
```

Prompt:

```text
broken hills outside the old capital, rolling dark stone and dry grass, ruined road pieces climbing between slopes, collapsed watch marker on a ridge, ancient civilization remains, center slope readable
```

### 05 highlands

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/highlands_01.webp
```

Prompt:

```text
windy highlands with exposed monolith bedrock, old standing stones, low clouds, distant ridges, fragments of ancient route markers, harsh expedition atmosphere, clear plateau in the center
```

### 06 mountains

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/mountains_01.webp
```

Prompt:

```text
mountain pass with ancient monolith stair remnants, steep cliffs, broken bridge foundation, cold wind, old watchtower ruins in the distance, no modern mountaineering elements, center path clear
```

### 07 swamp

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/swamp_01.webp
```

Prompt:

```text
dark swamp swallowing old monolith ruins, shallow black water, twisted trees, half-sunken road stones, rotten roots around ancient blocks, low mist, small dry combat mound in the center
```

### 08 marsh

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/marsh_01.webp
```

Prompt:

```text
cold marshland with reeds and flooded grass, old white-black stone markers half underwater, thin path of raised monolith slabs through the center, gray reflective pools, no modern boardwalk
```

### 09 jungle

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/jungle_01.webp
```

Prompt:

```text
overgrown jungle consuming ancient monolith architecture, huge leaves, vines over black and white stone, wet roots, ruined stairway in the background, dense but readable center clearing
```

### 10 savanna

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/savanna_01.webp
```

Prompt:

```text
dry savanna with ancient monolith remnants, golden grass, black acacia silhouettes, cracked stone road pieces, distant storm front, old marker stones leaning in the wind, center ground open
```

### 11 canyon

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/canyon_01.webp
```

Prompt:

```text
narrow canyon floor with ancient carved monolith walls, dry riverbed path, broken bridge anchors high above, layered stone cliffs, amber reflected light, clear combat lane through the center
```

### 12 badlands

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/badlands_01.webp
```

Prompt:

```text
red badlands basin with cracked earth and eroded stone fins, black monolith road fragments, dust haze, distant jagged ridges, ancient markers half buried, readable center area
```

## Batch 03 - System, Arena, Scenario, Remaining Fallbacks

### 01 wasteland

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/wasteland_01.webp
```

Prompt:

```text
ash wasteland beyond the old capital, blackened soil, dead stone trees, fractured monolith slabs, distant ruined towers, gray ash drifting, cold horizon glow, not pure black, clear center
```

### 02 city_ruins_generic

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/city_ruins_01.webp
```

Prompt:

```text
generic old capital ruins fallback, collapsed urban district made from ancient monolith stone, broken streets, fallen arches, shattered plazas, no clear landmark, usable for any D4 city ruins combat, clear center
```

### 03 hub_district_generic

Target path:

```text
src/frontend/static/images/game/backgrounds/biomes/hub_district_01.webp
```

Prompt:

```text
safe hub district inside D4 Citadel, poor survivor camp embedded in gigantic ancient architecture, portal shield shimmer in the distance, repaired tents and wooden platforms kept small, monolith plaza underfoot, no people
```

### 04 arena_duel

Target path:

```text
src/frontend/static/images/game/backgrounds/arena/duel_01.webp
```

Prompt:

```text
formal duel arena built inside an ancient monolith hall, circular cracked combat floor, black and white stone tiers, bronze repair rails, sealed side gates, warm torchlight mixed with faint ether-gold lines, no spectators
```

### 05 arena_team

Target path:

```text
src/frontend/static/images/game/backgrounds/arena/team_01.webp
```

Prompt:

```text
large team battle arena in the old capital, rectangular fighting ground, multiple ancient entry gates, broken spectator tiers, monolith pillars, clear lanes for groups, dim amber and ether-gold lighting, no modern sports arena
```

### 06 arena_chaotic

Target path:

```text
src/frontend/static/images/game/backgrounds/arena/chaotic_01.webp
```

Prompt:

```text
unstable chaotic arena chamber, fractured monolith floor, suspended stone fragments from ancient gravity damage, ritual pylons, old battle marks, subtle ether glow, dangerous but readable, no sci-fi machinery
```

### 07 arena_pending_gate

Target path:

```text
src/frontend/static/images/game/backgrounds/arena/pending_gate_01.webp
```

Prompt:

```text
arena staging gate before combat, dark monolith corridor opening into bright fighting hall, locked bronze-black gate mechanisms, floor channels glowing faint ether gold, empty waiting threshold, no characters
```

### 08 awakening_zero_shard

Target path:

```text
src/frontend/static/images/game/backgrounds/scenarios/awakening_zero_shard_01.webp
```

Prompt:

```text
Zero Shard awakening space, isolated fragment of reality outside the normal world, broken circular platform floating in a dark ether void, soft safe calibration light, monolith fragments suspended around it, surreal but calm, no city, no modern elements
```

### 09 awakening_combat_threshold

Target path:

```text
src/frontend/static/images/game/backgrounds/scenarios/awakening_combat_threshold_01.webp
```

Prompt:

```text
awakening combat threshold inside the Zero Shard, cracked monolith platform, dimensional fracture ahead, ether-gold calibration lines across the floor, distant abstract ruins fading into darkness, safe tutorial danger mood, clear combat center
```

### 10 rift_fantasy_ruin

Target path:

```text
src/frontend/static/images/game/backgrounds/rifts/fantasy_ruin_01.webp
```

Prompt:

```text
personal rift fantasy ruin, shard reality with broken ancient temple pieces floating slightly out of alignment, unnatural sky, monolith fragments mixed with foreign stone, core-path atmosphere, no monsters, clear center
```

### 11 sewer_toxic_tunnel

Target path:

```text
src/frontend/static/images/game/backgrounds/rifts/sewer_toxic_tunnel_01.webp
```

Prompt:

```text
ancient underground drainage tunnel beneath the old capital, narrow monolith channel, toxic green vapor low over shallow water, rusty primitive gate repairs, echoing chamber, no modern pipes, readable central path
```

### 12 neutral_unknown_fallback

Target path:

```text
src/frontend/static/images/game/backgrounds/fallbacks/unknown_scene_01.webp
```

Prompt:

```text
unknown ancient survival fantasy location, broken monolith floor, vague ruins fading into mist, faint ether-gold veins, enough detail to avoid black void, neutral mood, no specific biome, no modern elements, clear center for UI
```

## Future Anchor Overlay Prompts

These are not base fallback images. Use them later as overlays or alternate variants generated from a selected base image.

### stasis_north_overlay

```text
subtle stasis influence overlay, frost crystals along stone edges, suspended dust frozen in air, pale blue cold light, time-still atmosphere, preserve original environment composition
```

### entropy_south_overlay

```text
subtle entropy influence overlay, ash drift, heat shimmer, hairline cracks glowing dull red, eroded material edges, preserve original environment composition
```

### gravity_west_overlay

```text
subtle gravity storm influence overlay, small stone fragments floating upward, vertical lightning far in background, distorted dust trails, preserve original environment composition
```

### evolution_east_overlay

```text
subtle evolution influence overlay, creeping roots and tendrils, toxic spores in low air, wet green organic growth on cracks, preserve original environment composition
```

## Runtime Resolution Notes

Suggested context shape:

```json
{
  "background_url": "/static/images/...",
  "background_context": {
    "source": "exploration | arena | scenario | combat_result",
    "origin_state": "EXPLORATION | ARENA | SCENARIO",
    "location_id": "52_52",
    "zone_id": "D4_1_1",
    "biome_id": "city_ruins",
    "terrain_type": "ruin_road_main",
    "environment_tags": ["ruins", "street", "inner_wall"],
    "arena_mode": "duel | team | chaotic",
    "scenario_id": "awakening_rift",
    "scenario_node": "node_key",
    "anchor_influence": {
      "dominant_anchor": "stasis | entropy | gravity | evolution",
      "tags": ["frost", "time_stasis"]
    }
  }
}
```

Resolution order:

```text
1. Use exact `background_url` from exploration location if present.
2. If combat has scenario override, use scenario combat background.
3. If arena combat, choose stable random arena image from combat/session id.
4. If `terrain_type` has a fallback, use terrain image.
5. If `environment_tags` imply a stronger node type, use tag fallback.
6. If no node fallback exists, use `biome_id` fallback.
7. Later: apply/select anchor influence variant.
8. Last resort: neutral unknown fallback.
```

Important: the shell background and main stage should receive the same resolved `background_url`. CSS can dim, blur, and stretch the shell layer; data should not pick a separate image for the shell.
