# Rift Content And Lore Tasks

This file tracks rift content generation, lore, references, and future site communication.

## Settings

Rifts can represent almost any shard reality:

- Primal dinosaur world.
- Ice cave colony.
- Drifting ship fragment with breathable air.
- Techno-war world.
- Fungal moon.
- Fantasy ruin.
- Post-apocalyptic city.
- Bio-jungle.
- Cosmic horror zone.

Needs owner decision:

- First 3-5 MVP settings.
- Whether any setting is reserved for higher tiers only.

## Monster Families

Rifts should generate or select an inhabitant family first, then use weighted encounter placement.

Examples:

- Ice cave goblins.
- Lizard cave tribes.
- Fungal dinosaurs.
- Bio-hive drones.
- Techno-fanatic soldiers.
- Void-touched ship survivors.

Needs owner decision:

- Whether first families reuse existing monster resources or require new family resources.
- Whether LLM can create text only, while stats come from deterministic templates.

## LLM Content

LLM content should be ordered from structured tags and server-generated logic, not used as the source of gameplay truth.

Server owns:

- Tier.
- Size.
- Graph.
- Tags.
- Monster families.
- Encounter budget.
- Resource profile.
- Core placement.

LLM may produce:

- Rift overview description.
- Node descriptions.
- Atmosphere.
- Local names.
- Lore fragments.
- Symbiote commentary drafts.

Needs owner decision:

- Whether node descriptions are generated upfront, lazily, or only on discovery.
- How much content is persisted in DB.
- How strongly generated content should be moderated/validated before player display.

## Symbiote And Gift Lore

Symbiote is the internal entity explaining many player systems:

- Attributes.
- Physical skills.
- Gift interface.
- Rift perception.
- Adaptation.
- Core absorption.
- Resurrection explanation through AI/system imprint.

Gift is the magical/energetic development branch.

Needs owner decision:

- How visible the symbiote is as a speaking entity.
- Whether gifts unlock through rift cores, separate quests, or both.

## Site Roadmap / Voting

Future-facing site topics:

- Anchor rifts and regional suppression.
- Clan outposts around suppressed rifts.
- Portal circles and temporary teleport routes.
- Territory control around rift-thinned regions.
- Large raid rifts.
- Seasonal goals around four major anchors.
- Player or clan voting on which rift systems to prioritize.
- Public discovery records for first explorers.
