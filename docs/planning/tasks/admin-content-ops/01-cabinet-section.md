# Task 01 - Cabinet Content Ops Section

## Implementation Status

- [x] Local code implemented in `src/frontend/features/cabinet/modules/content_ops/`.
- [x] Registered in `src/frontend/cabinet.py`.
- [x] Covered by focused cabinet unit tests.

## Goal

Create a cabinet/admin section for operational content and database moderation
workflows. This is a shell/navigation task only; it should not add monster
regeneration, S3, or raw database mutation yet.

## Context

Current cabinet modules are registered in:

- `src/frontend/cabinet.py`
- `src/frontend/features/cabinet/modules/`
- `src/frontend/templates/site/base_cabinet.html`

The new area should group content operations separately from existing site,
game server, messaging, and analytics modules.

## Scope

- Add a `content_ops` or `database_moderation` cabinet module.
- Add a landing page with compact operational navigation.
- Expose intended subsections:
  - Monsters
  - News covers
  - Generated assets
  - Future: items, locations, users/moderation queues
- Keep it read-only and mostly empty until follow-up tasks implement data views.
- Update cabinet navigation/module registration using existing fastapi-cabinet patterns.

## Acceptance Checks

- `/admin` exposes a visible Content Ops / Database Moderation entry.
- The section renders under the cabinet layout without gameplay or public landing-page styling.
- Empty states are explicit and operational.
- No backend database tables are edited by this task.
- No generic raw SQL/table editor is introduced.

## Handoff Prompt

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-cabinet-design/SKILL.md
- docs/agent-skills/turnbasedmmorpg-design-system/SKILL.md

Task:
Implement the cabinet shell for a new Content Ops / Database Moderation area.
This is a navigation and landing-page task only. Do not add raw database editing,
monster regeneration, S3, or news image generation yet.

Relevant files:
- src/frontend/cabinet.py
- src/frontend/features/cabinet/modules/
- src/frontend/templates/site/base_cabinet.html
- src/frontend/static/css/cabinet.css
- docs/planning/tasks/admin-content-ops/01-cabinet-section.md

Rules:
- Cabinet UI must be dense, utilitarian, and scan-friendly.
- Frontend must not import backend internals or access backend DB directly.
- Reuse existing cabinet module patterns before adding new CSS.
- Do not create a generic Django-admin clone with unsafe table mutation.

Verification:
- Run the narrowest relevant frontend/cabinet tests if present.
- Start the app if needed and verify the /admin page renders the new section.
- Report which shared/cabinet component owns the layout and whether module-local CSS was added.
```
