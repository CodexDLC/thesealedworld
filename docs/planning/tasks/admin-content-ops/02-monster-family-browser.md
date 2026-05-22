# Task 02 - Monster Family Browser

## Implementation Status

- [x] Backend generated monster projection exposes visual/storage/equipment metadata.
- [x] Frontend backend API client and Content Ops monster list/detail UI added.
- [x] Covered by focused backend projection/API and cabinet tests.

## Goal

Build a read-only cabinet browser for generated monster families/clans and their
members. This makes existing production data inspectable before regeneration or
S3 migration work begins.

## Context

Backend already has a generated monsters admin endpoint:

- `src/backend/features/monsters/api/router.py`
- `src/backend/features/monsters/services/generated_view_service.py`
- `src/backend/features/monsters/repositories/monster_generation_repository.py`

The current response is summary-oriented. The cabinet view needs richer visual
and member detail data.

## Scope

- Add or extend backend admin DTOs for generated monster family details.
- Expose family/clan visual data:
  - image URL
  - storage key
  - storage backend
  - description
  - tier/zone/family identifiers
- Expose member detail data:
  - image URL
  - storage key/backend
  - role, tier, threat rating, gear score
  - equipment summary
  - affix/bonus summary when present
  - armor/weapon summary when present
- Add a typed frontend backend API client method.
- Add a cabinet read-only list/detail UI under Content Ops -> Monsters.
- Add filters for family, role, storage backend, and missing image.

## Acceptance Checks

- Admin can open a monster family/clan detail page.
- Family image and member images render from their stored URLs.
- Missing image/data states are visible, not silently hidden.
- Members are shown in a stable order.
- No regeneration or mutation buttons are wired in this task.
- Tests cover the backend projection for family/member visual and equipment data.

## Handoff Prompt

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- docs/agent-skills/turnbasedmmorpg-backend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-cabinet-design/SKILL.md
- docs/agent-skills/turnbasedmmorpg-testing-strategy/SKILL.md

Task:
Implement a read-only Content Ops -> Monsters browser for generated monster
families/clans and their members. The UI should show family image/description
and member details including role, tier, gear score, equipment, affixes/bonuses,
and member image metadata. Do not add regeneration or S3 changes yet.

Relevant files:
- src/backend/features/monsters/api/router.py
- src/backend/features/monsters/dto/generated_view.py
- src/backend/features/monsters/services/generated_view_service.py
- src/backend/features/monsters/repositories/monster_generation_repository.py
- src/frontend/integrations/backend_api/
- src/frontend/features/cabinet/modules/
- docs/planning/tasks/admin-content-ops/02-monster-family-browser.md

Rules:
- Backend monsters feature owns monster projection logic.
- Frontend must consume backend data through a typed backend API client.
- Cabinet UI must favor tables, dense lists, filters, and explicit empty states.
- Do not add a raw table editor.

Verification:
- Add focused backend tests for the generated monster detail projection.
- Add frontend/cabinet tests if the repo has an established pattern for these modules.
- Run the narrowest relevant pytest commands with --no-cov if appropriate.
```
