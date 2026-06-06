# Backend Content Text Bootstrap Contract

Status: postponed idea, not an implementation task.

This note captures the agreed direction for a future backend content-text
contract. Localization work is intentionally deferred. The purpose is to make
the idea recoverable later without rebuilding it from chat history.

## Problem

Player-facing text is currently stored and emitted differently across backend
features. Some resources keep ready strings in gameplay JSON, some DTOs expose
`title`/`description`/`label`, some content uses `name_ru`, and combat catalog
resources already have a cleaner split between technical and descriptive data.

This makes future multilingual support and client-side text caching harder than
needed. The backend needs a stable content model first; frontend rendering and
URL-based language routing are separate future tasks.

## Target Direction

Backend catalog/resource entries that can be exposed through bootstrap should
move toward one shared shape:

```json
{
  "key": "item.weapon.short_sword",
  "technical": {},
  "descriptive": {
    "ru": {
      "title": "...",
      "description": "..."
    },
    "en": {
      "title": "...",
      "description": "..."
    }
  }
}
```

The combat catalog pattern is the reference point:

- `key` is the stable content identifier.
- `technical` contains gameplay data: math, balance, formulas, effects,
  requirements, transitions, rewards, targeting, and engine flags.
- `descriptive` contains player-facing text only.

Language should be a top-level key inside `descriptive`, not scattered across
fields like `title_ru`, `title_en`, `description_ru`, and `description_en`.

## Bootstrap Role

The future bootstrap/catalog collector should not be a UI renderer. Its job is
to walk backend catalog providers, gather entries by stable `key`, select the
requested language with fallback rules, and build packages that the client can
cache in IndexedDB.

Expected responsibility:

```text
backend catalog providers
  -> entries with key / technical / descriptive
  -> bootstrap package builder
  -> client cache payload
```

The initial loading strategy should probably be hybrid:

- core bootstrap: common catalogs needed early, such as items, skills,
  attributes, combat references, and basic game dictionaries;
- lazy packages: large narrative or progression-bound content, such as
  scenarios, rifts, location packs, generated world content, and future chapter
  packs.

## Scope Boundary

This idea is backend-first.

It does not include:

- implementing frontend templates;
- sending static UI labels for normal frontend-owned buttons;
- switching website routes to `/ru/...` and `/en/...`;
- introducing PO files as the primary content system;
- rewriting all game content in one patch.

Frontend can later consume the backend packages and use its own bootstrap for
frontend-owned UI text.

## Feature Migration Direction

Future feature-specific tasks should convert their own resources toward this
contract without designing the global bootstrap themselves.

Likely high-impact areas:

- items and item resources;
- monsters, generated clans, and generated encounter text;
- world locations and exploration descriptions;
- rift master/node JSON resources;
- scenario node/dialog/action JSON resources;
- backend-owned runtime labels and log/event text that are not frontend UI.

For scenario and rift content, gameplay fields should stay separate from
narrative fields. A node should still have technical fields such as keys,
actions, transitions, effects, gates, and tags, while text moves under the
descriptive language structure.

For taxonomy/body-type variants, taxonomy should live inside each language
block rather than competing with language at the same level:

```json
{
  "descriptive": {
    "ru": {
      "variants": {
        "humanoid": {},
        "beast": {}
      }
    },
    "en": {
      "variants": {
        "humanoid": {},
        "beast": {}
      }
    }
  }
}
```

## Prompt Shape For Future Parallel Tasks

Common prompt block:

```text
We are not implementing frontend localization now. The current backend goal is
to prepare this feature's content resources for a future bootstrap/catalog
collector.

Use the shared content-entry direction:
- key: stable content identifier;
- technical: gameplay/engine data only;
- descriptive: player-facing text only, with language as the top-level key
  inside descriptive.

Do not design the global bootstrap in this feature task. Convert or propose the
feature-local resource shape so a later bootstrap provider can read it
consistently.
```

Feature-specific prompts should then name the exact module and ask only for that
module's resource/DTO/provider design or migration plan.
