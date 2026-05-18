---
name: turnbasedmmorpg-generation-ai-determinism
description: Deterministic AI generation and template-hash rules for TurnBasedMMORPG. Use when changing generation_ai tasks, AI prompt payloads, generated item text/image templates, item generation hashes, monster-owned generated content, rift-generated content, or any service that stores/reuses AI output by hash.
---

# TurnBasedMMORPG Generation AI Determinism

## First Reads

Read with:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-item-resources/SKILL.md` for item generation
- `docs/agent-skills/turnbasedmmorpg-monster-family/SKILL.md` for monster-owned generated content

## Core Rule

Separate template identity from prompt richness.

- Template hash payload is the minimal stable identity used to reuse generated output.
- Prompt payload may be richer and may include descriptive source context.
- Item instance ids, placement, locations, combat actor ids, affix rolls, transient runtime data, and raw `source_context` must not enter a reusable template hash unless the product owner explicitly makes that field part of template identity.

## Item Text Template Hash

Persisted item text templates are keyed only by:

```text
clan_id + base_id + item_tier + material_id
```

The hash function may wrap this payload with the prompt version so prompt-contract changes create a new template generation space.

Do not include in the item text template hash:

- `location_id`
- `source_tier`
- `owner_family` object
- `loot_culture` object
- `family_id` when `clan_id` is available
- `member_role`
- `variant_key`
- `item_id`
- placement data
- affix ids, bundles, or roll values

Prompt payload may still include `source_context`, `owner_family`, and `loot_culture`; those fields help the AI write the text but do not define template identity.

For persisted item AI text, generated clan narrative must come from the database by `clan_id`.

- Treat Python/JSON monster family resources as generation templates only.
- Do not trust an event-provided `owner_family` object as the source of truth for item prompt narrative.
- If `clan_id` is present, load the generated clan row and use its persisted `name_ru`, `description`, `raw_tags`, and `flavor_content.loot_culture`.
- If a `clan_id` is invalid or missing in the DB, fail the AI text task instead of falling back to static family resources or stale payload data.

## Monster Runtime Items

Monster runtime item projections are combat inputs, not player loot templates.

- Natural monster equipment such as claws, teeth, shells, or hides may exist as runtime combat projections.
- Natural equipment must not enqueue persisted item AI text.
- Natural equipment must not become player equipment loot by itself.
- Natural monsters drop resources, ingredients, salvage, or other configured loot resources, not persisted equipment instances.

## AI Task Identity

When an AI output belongs to a reusable template, prefer task identity based on the template hash or generated template id, not a concrete item instance id.

Using item instance ids in task identity is only correct when the generated output is truly unique to that item instance.

## Verification

For item text hash changes, run:

```powershell
.\.venv\Scripts\pytest.exe tests\backend\features\items\test_generation_service.py tests\backend\features\items\test_item_text_service.py --no-cov
```

Add focused tests proving that fields excluded from the template hash do not create new templates.
