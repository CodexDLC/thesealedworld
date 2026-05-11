---
name: turnbasedmmorpg-skill-builder
description: Project agent-skill authoring rules for TurnBasedMMORPG. Use when creating, updating, reviewing, or organizing Codex/agent skills under docs/agent-skills/, especially to avoid confusing agent skills with the in-game skill catalog.
---

# TurnBasedMMORPG Skill Builder

## Purpose

Use this skill when the user asks for a skill for agents, Codex, project workflow, project memory, task rules, handoff rules, or `docs/agent-skills/`.

Do not use this skill for in-game character skills. In-game skills are owned by `src/backend/features/game_catalog/skills` and covered by `turnbasedmmorpg-skill-catalog`.

## Location

Project agent skills live here:

```text
docs/agent-skills/<skill-name>/SKILL.md
```

Use lowercase hyphen-case for `<skill-name>`, normally prefixed with `turnbasedmmorpg-`.

Examples:

```text
docs/agent-skills/turnbasedmmorpg-backend/SKILL.md
docs/agent-skills/turnbasedmmorpg-skill-builder/SKILL.md
```

## Required Shape

Every project agent skill must have one `SKILL.md` with YAML frontmatter:

```markdown
---
name: turnbasedmmorpg-example
description: Clear trigger text. Use when ...
---
```

Only `name` and `description` are required in frontmatter. Put trigger conditions in `description`, because agents see that before loading the skill body.

## Writing Rules

- Keep the skill short and operational.
- Write rules that change agent behavior in this project.
- Prefer exact paths over vague module names.
- Link only the files the agent should actually read.
- Separate "read first", "ownership", "do", "do not", and "verification" when useful.
- Do not add README, changelog, quick reference, or other auxiliary docs unless the user explicitly asks.
- Do not create code, tests, app features, or runtime migrations when the request is only to create an agent skill.

## Project Rules

Before creating or updating a project agent skill, read:

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md`
- any existing skill that overlaps the requested topic

If the skill affects backend, frontend, CSS shell, Redis, item resources, monsters, combat, or in-game skill catalog work, reference the existing relevant project skill instead of duplicating its full content.

## Common Mistake

When the user says "skill for you agents", "agent skill", "skill in the project for Codex", or "docs/agent-skills", create or update a project agent skill under `docs/agent-skills/`.

Do not edit:

```text
src/backend/features/game_catalog/skills
tests/backend/features/game_catalog/skills
```

unless the user explicitly asks for in-game character skill catalog work.

## Minimal Creation Workflow

1. Normalize the requested name to lowercase hyphen-case.
2. Create `docs/agent-skills/<name>/SKILL.md`.
3. Write concise frontmatter with a strong `description`.
4. Add only the project-specific rules needed for agents to do the task correctly.
5. Run a narrow sanity check:

```powershell
Get-Content docs\agent-skills\<name>\SKILL.md
```

6. Report the file created and any relevant limitation. Do not claim runtime tests are needed for docs-only skill changes.
