---
name: turnbasedmmorpg-cabinet-design
description: Cabinet/admin design rules for TurnBasedMMORPG. Use when designing or editing cabinet pages, admin/management dashboards, operational panels, analytics surfaces, moderation tools, or cabinet module UI.
---

# TurnBasedMMORPG Cabinet Design

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-design-system/SKILL.md`

## Scope

This skill covers operational cabinet/admin surfaces, not the public site and not gameplay HUDs.

Examples:

- cabinet module pages
- admin dashboards
- analytics tables
- moderation/management panels
- backend/game-server status views

## Core Rules

- Cabinet UI is utilitarian and information-dense.
- Do not use landing-page hero composition in cabinet surfaces.
- Do not use gameplay HUD framing as the base for cabinet tools unless a specific embedded game preview requires it.
- Prioritize scanability, stable tables, predictable navigation, filters, status badges, and compact controls.
- Reuse cabinet shell/components before adding module-local CSS.

## CSS Ownership

Use this order:

1. tokens
2. common components
3. cabinet shell
4. cabinet components
5. module CSS

Module CSS may arrange module content, but shared cabinet navigation, panel chrome, table behavior, filter bars, and toolbar behavior belong in cabinet components.

## Layout Rules

- Keep repeated operational items in tables, dense lists, or compact panels.
- Use cards only for repeated item summaries or bounded widgets, not as a default page-section wrapper.
- Controls should be close to the data they affect.
- Long-running or unavailable data should have explicit loading, empty, and error states.

## Required Self-Check

Before finishing cabinet UI work, report:

- Which cabinet/shared component owns the behavior.
- Which module class only customizes content.
- Whether any public-site or gameplay class was incorrectly reused.
