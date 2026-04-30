---
name: turnbasedmmorpg-project
description: Project-wide architecture guidance for TurnBasedMMORPG. Use before changing repository structure, moving code between temp/src, creating new features, touching shared contracts, or preparing handoff prompts for another agent in this project.
---

# TurnBasedMMORPG Project

## First Reads

Read these before broad architecture work:

- `docs/agent-skills/turnbasedmmorpg-project/references/project-rules.md`

For event-driven or cross-feature backend work, also use `turnbasedmmorpg-redis-streams`.
For frontend feature/template/static work, also use `turnbasedmmorpg-frontend`.
For backend feature/API/service/repository work, also use `turnbasedmmorpg-backend`.

## Operating Rules

- Treat `src/` as the target source tree.
- Treat `temp/` as donor code only; do not copy its old architecture directly.
- Keep frontend and backend separated by HTTP/API contracts.
- Keep shared code narrow and stable; do not put one-side-only models into `src/shared`.
- Prefer feature-owned modules over global managers, global repositories, or a central dispatcher.
- Keep changes scoped to the active feature unless a documented architecture rule requires otherwise.

## Handoff Prompt Shape

When preparing another agent or chat, include:

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- <specific related skill>

Task:
<specific task>

Relevant files:
- <exact paths>

Rules:
- <project rules that matter>

Verification:
- <commands or manual checks>
```
