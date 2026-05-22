# Rift Open Questions

Use this file to track decisions that should be clarified with the project owner before or during implementation.

## Terminology

Use `project owner` for the human design decision maker. If a task needs a Russian label in notes, use `владелец дизайна`.

## Personal Rifts

- What exact mix of 5-6 notices should the board show?
  - Easier farm.
  - Equal-tier standard.
  - Hard-tier risk.
  - Resource task.
  - Kill-family task.
  - Core-closure task.
- Should contracts be pure UI choices, NPC quests, physical coordinate items, or all three?
- How strongly should entrance distance affect reward?
- Should first personal rifts allow party entry?
- How much of a reused template should change for a new player?

## Core Handling

- Is extraction its own skill, or part of an existing gathering/crafting skill?
- What are the first core actions?
  - Break.
  - Absorb by symbiote.
  - Extract dust.
  - Extract broken shard.
  - Extract whole shard.
- Does failed extraction always destroy part of the core?
- Does symbiote absorption compete with material reward?

## Symbiote

- Does symbiote tier directly scale stats, or mainly unlock protection/interface/core handling?
- What is the player-facing name for the seven symbiote ranks?
- How much does the symbiote talk in UI?
- Can symbiote tier block entry into higher-tier rifts?

## Dirty Loot And Death

- Is dirty loot loss active from tier 1?
- Does MVP include corpse recovery?
- If no corpse recovery in MVP, does death delete dirty loot or mark it as future-recoverable?
- Can party members recover another member's corpse/cache?

## Encounter Budget

- What initial divisor converts total GS to encounter budget?
- What is `party_tier`: symbiote tier, gear tier, average item tier, or derived readiness tier?
- How much overbudget can a generated encounter use?
- Can a combat-required rift still have empty or very easy nodes?
- Should the encounter builder include player role composition, or only GS in the first version?

## Anchor Rifts

- Who owns anchor rift access: clan, party, region, or public server?
- How is access shared with resource gatherers after combat groups clear a floor?
- Is the core removed permanently, suppressed temporarily, or reactivated after a timer?
- Does full closure of four major anchors end a season, or only open a strategic window?
- What is the smallest useful anchor-rift slice before full raids?

## Resources

- Are resource spots depleted per instance, per clan, per server cycle, or per template?
- Can gatherers enter already-cleared floors without combat roles?
- How much risk remains on cleared floors?
- Which skills affect rift gathering first?

## Browser Interface (Resolved Decisions)

- **Map visualization:** The UI displays a stylized, high-tech neon "Symbiote Scanner" (Event Graph Map) instead of a literal retro 2D grid. The central viewport shows a gorgeous AI-generated scene artwork, the current encounter state, and contextual action buttons.
- **Node & Text Generation:** Generation is lazy and modular. It happens in three stages (Skeleton $\rightarrow$ Spawn $\rightarrow$ AI Narrative Writer) per **3x3 Sector**.
- **Visibility & Scouting:** Standard "fog of war" hides unscouted sectors. Symbiote acts as a scanner, highlighting adjacent nodes' threat levels, resources, and lore comments before entering.
- **Symbiote Commentary:** Rendered as clean, atmospheric overlay messages, holographic audio-logs, or subtle side-dialogue panels in the text card area, ensuring it feels organic rather than intrusive.
