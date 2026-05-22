# Task 03 - Monster Visual Regeneration

## Implementation Status

- [x] Backend admin endpoints enqueue clan/member image regeneration tasks.
- [x] Cabinet detail actions added for explicit per-entity regeneration.
- [x] Previous image URL is preserved while a new task is pending.
- [x] Covered with fake-tested API/service-adjacent unit tests; no real AI provider call.
- [ ] Real provider smoke test pending credentials/runtime.

## Goal

Add cabinet actions to regenerate images for a generated monster family/clan and
for individual generated monster members.

## Context

Existing generation paths include:

- `src/backend/features/monsters/tasks_ai.py`
- `src/backend/features/monsters/scripts/regenerate_images.py`
- `src/backend/features/generation_ai/`
- `src/backend/features/monsters/resources/visuals.py`

This task should first work with the current local generated asset storage. S3
is a later task.

## Scope

- Add backend admin endpoints for:
  - request family/clan image regeneration
  - request member image regeneration
  - poll or inspect task status/result
- Reuse existing AI generation task infrastructure.
- Preserve stable `storage_key` semantics.
- Update generated monster metadata after success:
  - `image_url` / `generated_image_url`
  - `storage_key`
  - `storage_backend`
  - generation metadata
- Add cabinet buttons and loading/error/success states.
- Require an explicit admin action; no automatic bulk regeneration.

## Acceptance Checks

- A family/clan detail page has a regenerate image action.
- Each member detail row/card has a regenerate image action.
- UI shows pending, failed, and completed states.
- Failed regeneration does not remove the previous working image.
- New images still use the generated asset storage abstraction.
- Tests cover success and failure paths without calling the real AI provider.

## Handoff Prompt

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- docs/agent-skills/turnbasedmmorpg-backend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-cabinet-design/SKILL.md
- docs/agent-skills/turnbasedmmorpg-redis-streams/SKILL.md
- docs/agent-skills/turnbasedmmorpg-testing-strategy/SKILL.md

Task:
Add admin/cabinet regeneration actions for generated monster family/clan images
and generated monster member images. Start with the existing generated asset
storage backend; do not implement S3 in this task.

Relevant files:
- src/backend/features/monsters/tasks_ai.py
- src/backend/features/monsters/scripts/regenerate_images.py
- src/backend/features/monsters/api/router.py
- src/backend/features/monsters/services/
- src/backend/features/generation_ai/
- src/frontend/features/cabinet/modules/
- src/frontend/integrations/backend_api/
- docs/planning/tasks/admin-content-ops/03-monster-visual-regeneration.md

Rules:
- Do not call AI providers in tests.
- Do not delete or overwrite the previous valid image metadata until the new task succeeds.
- Do not bypass feature integrations or task infrastructure.
- Keep admin actions explicit and per-entity.

Verification:
- Add focused backend tests using fakes/in-memory doubles for generation task execution.
- Verify cabinet UI renders pending, failed, and completed states.
- Confirm previous image remains visible on failed regeneration.
```
