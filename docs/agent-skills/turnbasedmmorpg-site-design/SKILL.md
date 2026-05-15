---
name: turnbasedmmorpg-site-design
description: Public/site design rules for TurnBasedMMORPG. Use when designing or editing the public website, landing pages, library/news/about/auth pages, marketing sections, or non-game public site templates and CSS.
---

# TurnBasedMMORPG Site Design

## First Reads

Read:

- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-design-system/SKILL.md`

## Scope

This skill covers the public site and account-facing website surfaces, not gameplay HUDs and not cabinet/admin tools.

Examples:

- landing pages
- public library/news/about pages
- login/register pages and modals
- site header/footer
- promotional or explanatory content

## Core Rules

- Site design may be more editorial, atmospheric, and brand-led than gameplay UI.
- Do not apply site landing-page patterns to the game HUD.
- Reuse site tokens, typography, buttons, cards, and includes before adding page CSS.
- If a site component appears on multiple pages, move it to a site/shared component instead of duplicating it in page CSS.
- Keep marketing sections separate from operational cabinet UI and gameplay shell UI.

## CSS Ownership

Use this order:

1. tokens
2. common components
3. site includes/header/footer
4. site components
5. page CSS

Public site CSS must not redefine gameplay shell selectors or cabinet layout selectors.

## Visual Direction

- First viewport should clearly signal the product/world when the page is branded.
- Use real or generated imagery when the page needs emotional/visual context.
- Avoid turning the public site into a dense operational dashboard.
- Keep calls to action clear and reusable.

## Required Self-Check

Before finishing site UI work, report:

- Which site/shared component was reused or added.
- Whether any gameplay or cabinet class was incorrectly reused.
- Whether page-local styles should be promoted.
