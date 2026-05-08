# Rift Core Design

This document captures the current design direction for rifts as a core game mechanic. It is a planning artifact, not a frozen implementation spec.

## Design Sources

- `docs/game-design/designer/world/05_game_loops.md`
- `docs/game-design/designer/world/03_threat_and_anchors.md`
- `docs/game-design/designer/world/04_interaction_and_scouting.md`
- `docs/game-design/designer/economy/02_risk_and_sync.md`

## External References And Boundaries

External references are used for tone, structural inspiration, and design discussion only. Do not copy settings, names, factions, lore text, or proprietary mechanics.

- `Кодекс Охотника` by Юрий Винокуров and Олег Сапфир:
  - Useful references: hunters, rifts/anomalies, threat tiers, monster pressure, social structures around dangerous zones, hunting contracts.
  - Project translation: adventurers guild contracts, rift tiers, local anomaly influence, monster families, and player-facing risk/reward loops.
- Константин Муравьёв, including EVE-online / Содружество-inspired and fantasy survival cycles:
  - Useful references: closed or alien worlds, survival progression, harsh expedition pacing, internal growth systems, symbiote-like development fantasy, dangerous world traversal.
  - Project translation: symbiote progression, multiverse shard worlds, rift core absorption, survival/extraction pressure, and progression through increasingly hostile tiers.

Project-specific identity:

- Rifts are multiverse shards.
- Gifts and the symbiote are project-owned progression systems.
- The browser interface expands beyond old Telegram-style button gameplay.
- Clan territory, anchor rifts, portal circles, outposts, and regional suppression are project-specific MMO layers.

## Core Concept

Rifts are shards of other realities from the multiverse. A rift can be a primal dinosaur valley, an ice cave colony, a drifting ship fragment in space, a techno-war world, a fungal moon, a fantasy ruin, a post-apocalyptic city, or a high-level raid-scale anchor reality.

The technical shape can be a graph of points of interest, but the player-facing fantasy is not a small room dungeon. A node may represent a valley, cave chamber, ship deck, battlefield, grove, mining pocket, ruined street, or other scene.

Every rift has one central goal:

- Find the rift core.

Core outcomes depend on rift type, player progression, and future systems:

- Break it into rift dust or fragments.
- Extract a whole shard.
- Extract a higher-quality crystal.
- Let the symbiote absorb it for bonus experience or progression.
- Suppress or close an anchor rift to change regional control.

## Shared Rift Axes

- `tier`: 1-7, driving danger, resource tier, reward quality, encounter strength, and preparation requirements.
- `size`: small, medium, large, colossal; drives run length, floor count, node count, and resource density.
- `setting`: the reality theme.
- `ruleset`: distorted laws of the shard world.
- `inhabitants`: local monster families or civilizations.
- `dominant_threat`: the main kind of danger, not only numeric strength.
- `stability`: how long the rift can persist and how unstable it becomes.
- `resource_profile`: gathering and rare substance distribution.
- `core_state`: intact, discovered, extracted, absorbed, broken, suppressed.

## Personal Rifts

Personal rifts are the main repeatable PvE loop.

```text
Town / tavern / adventurers guild board
  -> player chooses one notice from the contract board
  -> personal rift instance is prepared while the player travels to the entrance
  -> player enters and explores
  -> player finds the core
  -> player extracts, breaks, or feeds the core to the symbiote
  -> rift ends for that player
```

Rules:

- The board should look like an adventurers guild notice board with 5-6 posted paper notices.
- Notices are generated for the character and can include weaker, equal, and harder-than-current-tier options.
- Each notice exposes setting/risk/reward clearly enough for the player to choose a run style.
- A specific personal rift instance is completed by a character only once.
- Early players may act as first explorers that cause new rift designs/templates to be generated.
- Later contracts may reuse suitable stored templates by tier, setting, tags, size, and quest requirements.
- Reused templates still vary points of interest, monster placement, resource placement, and event rolls.
- Personal rifts are visible only to the player or group that owns the instance.

Contract types:

- Close a rift by reaching and resolving its core.
- Kill monsters from a specific rift-linked clan/family.
- Retrieve quest items from a specific rift type.
- Gather resources from a specific rift setting or tier.
- Hunt monsters near a rift if their family has leaked into the surrounding region.

## Contract Location And Travel

After a notice is accepted, the game creates or selects an entrance point in the world.

- Tier 1 rifts can appear near safer outer zones.
- Tier 2-3 rifts should require travel into matching danger regions.
- Higher tiers should require deeper expedition routes, stronger preparation, or portal access.

Travel is part of the risk and pacing. A tier 3 rift may reasonably require 5-10 minutes of travel from the city if the player has no portal route. This makes portal infrastructure and controlled routes meaningful.

Future portal systems:

- City-to-outpost portals.
- Clan-built portal circles.
- Temporary portals opened after anchor suppression.
- Discovered region gates.

## Public Rift Outbreaks

Most personal contract rifts are hidden from other players to avoid turning the basic PvE loop into forced PvP.

Future public outbreaks:

- Rifts appear as anomaly eruptions in the open world.
- Any eligible player or group can discover and enter them.
- They can become contested PvE/PvP-adjacent objectives.
- They leak monsters and resources into nearby regions.
- They bridge solo contracts and anchor-scale content.

## Anchor Rifts

Anchor rifts are not MVP. They are the long-term clan, raid, territory, and server-scale layer.

Anchor rifts are:

- Region-bound.
- Multi-level or multi-floor.
- More fixed in structure than personal rifts.
- Suitable for real map rendering.
- Shared through clan, party, or server access rules.
- Built around bosses per floor and a major core.
- Persistent while the core remains intact.
- Connected to territory suppression, portal circles, outposts, and high-level progression.

Future flow:

```text
Anchor rift discovered
  -> first floors generated
  -> raid groups clear combat pressure
  -> resource groups gather from secured floors
  -> deeper floor descriptions are generated lazily
  -> floor bosses are defeated
  -> clan decides whether to continue farming or remove/suppress the core
  -> portal circle becomes active for a limited time
  -> clan can build an outpost
  -> city teleport and regional influence changes unlock
```

Anchor rifts can be ultra-high-end PvE for large raid groups. Their final closure behavior is unresolved: permanent seasonal closure, temporary suppression, or recurring reactivation.

## Anchor Regional Influence

Anchor rifts thin the world fabric around their sub-region.

Nearby exploration encounters may include:

- Normal local monsters.
- Rift-linked monster families.
- Rift resource leaks.
- Rift visual and lore effects.
- Higher anomaly pressure.

## Graph And Nodes

Rifts use graph structure, but graph nodes are interpreted flexibly.

Suggested node data:

```text
node_id
node_type
tags
description
connected_nodes
resource_possible
encounter_possible
boss_possible
core_possible
gathering_profile
danger_profile
```

Structure and descriptions may be stable. Concrete events can be rolled per instance or per visit.

## Template Versus Instance

```text
RiftDesignTemplate
  stable design, setting, tags, graph shape, node descriptions, inhabitant family, possible events

RiftInstance
  player/group/clan-specific copy with chosen layout variations, event placement, monster placement, resource charges

RiftRunState
  live progress, current node, discovered nodes, killed monsters, gathered resources, dirty loot, core state
```

Store template setting, tags, graph, node descriptions, possible event pools, inhabitant family, resource profile, visit history, and first-discovery metadata. Avoid hard-storing every minor event roll unless it matters to persistence or player history.

## Confirmed Decisions

- First playable rifts are quest rifts.
- Personal rifts are single-completion per character.
- Rift encounters are assembled from solo/group/raid gear-score budget.
- Higher tier means larger or more complex interiors, higher reward quality, better monster loot bands, more dangerous inhabitants, and more demanding preparation.
- Symbiote has 7 tiers and progresses primarily through rifts/rift energy.
- Symbiote explains attributes, physical skill expression, gift interface, rift perception, adaptation, core absorption, and resurrection fantasy.
- Core handling depends on extraction/gathering skill versus rift tier.
- Rifts always have combat pressure.
- Personal MVP rewards lean toward monster drops and rift substances rather than peaceful mining.
- Dirty loot becomes secured only through safe sync zones such as city return or portal arcs.
- Death in a rift loses dirty loot unless recovered from corpse/cache.
- Travel to the rift is gameplay.
- Reused templates must at least vary monster placement and reward/resource placement.
