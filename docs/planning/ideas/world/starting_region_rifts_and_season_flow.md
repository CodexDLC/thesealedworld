# Starting Region Rifts And Season Flow

## D4 Start Region

D4 is the ruined old capital around the protected hub. Safe status and tier are separate:

- Hub core, 5x5 nodes: `is_safe_zone=true`, tier 0, no monster population.
- Main gate cross and ordinary ruined streets: `is_safe_zone=false`, family tier 1, standard starter encounters.
- Corner pressure districts: tier 1, with stable context tags for hash separation.
- Four city rift nodes: tier 2 pressure sources. They are not lairs; they are active spatial breaks that let local monsters leak into the city ruins.

The four MVP D4 city rifts are:

- `d4_rift_rat_king`: rat swarm pressure from the undercity seep.
- `d4_rift_wolf_breach`: wolf pack pressure from overgrown kennels and park ruins.
- `d4_rift_bandit_barricade`: bandit pressure around a controlled barricade node.
- `d4_rift_goblin_scrapyard`: goblin pressure around collapsed workshops and scrap piles.

The rifts are future gate-lock sources. Closing them should unlock or prepare the city gates and give players enough equipment and materials to survive outside the walls.

## Monster Context Hash

Monster clan context is based on:

- biome id,
- family/clan tier,
- normalized context tags.

D4 rift and starter-region tags must be preserved for hashing, not filtered out as only mutation tags. This lets tier 1 starter streets, tier 1 corner pressure, and tier 2 rift nodes generate separate clan contexts.

Family selection can use stable context tags such as `rat_swarm`, `wolf_pack`, `bandit_gang`, and `goblin_tribe` for rift-biased contexts.

## Family Tier Progression

Clan tier is the scaling tier. Variant availability is broad:

- family tier 1 can use variant tiers 0..2,
- family tier 2 can use variant tiers 0..3.

Selected members scale from the family tier. Higher-tier clans therefore become stronger and can include broader compositions while weak roles remain available.

## Outer World Direction

Outside D4, the hub portal should not globally flatten danger. Regional progression should come from pressure sources:

- each region can have a central descriptive rift or rupture,
- outposts can be built near these sources to simplify survival, storage, repair, routes, and regional tasks,
- deeper zones approach true anchor influence,
- the late season focuses on weakening or closing anchor cores.

Season scoring should track objective contribution, not only kills:

- rift and anchor closure progress,
- outpost construction and defense,
- scouting and route discovery,
- boss and elite encounter contribution,
- delivered resources and relics,
- combat support such as damage, tanking, healing, and utility.
