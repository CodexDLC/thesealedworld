---
name: turnbasedmmorpg-release-flow
description: Release stages, branch strategy, wipe-risk classification, and version bumping rules for The Sealed World. Use before deciding which branch a change goes into, what version number to bump to, whether work needs a player-progress wipe, or how to phrase an Unreleased changelog entry. Also use before merging into main, cutting a release tag, planning a wipe announcement, or changing the stage/version values exposed on the landing.
---

# TurnBasedMMORPG Release Flow

## Purpose

Give every change an unambiguous answer to three questions:

1. **Which branch does this go into?**
2. **What does it do to the version number?**
3. **Does it require wiping player progress and, if so, what announcement is owed?**

This skill is the source of truth for those three. Other release-adjacent skills
(changelog discipline, deployment ops) follow the decisions made here.

## Read First

- `docs/agent-skills/turnbasedmmorpg-changelog-release/SKILL.md` — how Unreleased entries and tag summaries are written.
- `docs/agent-skills/turnbasedmmorpg-deployment-management/SKILL.md` — compose layers, image tags, manual deploy gates.
- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md` — repository-wide rules and skill umbrella.

## Stage Model

The public surface uses exactly three stages. They are stored in
`FrontendSettings.release_stage` (default `alpha`) and rendered by
`UIRenderer` as `release_stage_label` for the landing/footer.

| Stage | Player promise | When it applies |
|---|---|---|
| `alpha` | Active development with players as testers. Progress may be reset at major changes — always announced, never as a surprise. | Until the project considers core systems stable enough that future wipes are unlikely. |
| `beta` | Stabilisation. Progress is kept. At most one announced wipe before 1.0, minimum 30 days notice. | Between "core stable" and the first real release. |
| `release` | 1.0+. Progress is not reset. Future work is patches, minor features, and expansions. | After the project ships 1.0. |

The stage is a separate signal from the version number. Do not encode the
stage into the version (no `0.x = alpha, 1.x = beta` schemes). Stage moves
rarely; the number moves continuously.

There is no `closed-beta` / `open-beta` split. Open versus closed
participation is handled with feature flags or invites, not with a new stage.

## Branch Strategy

Three long-lived branches plus short-lived ones, no exceptions:

```text
main              prod. Only fully prepared changes land here. Every merge tags a release.
develop           "next minor". All feature work, refactors, balance, content edits accumulate here.
hotfix/<topic>    short-lived; branched from main; back-merged into main AND develop.
release/wipe-<X>  carantine for code that will need a player-progress wipe; not merged into develop until announcement window has passed.
```

The decision flow for a new change:

1. **Is this a bug that needs to ship today?** -> `hotfix/<topic>` from `main`.
2. **Does this change require a wipe?** -> `release/wipe-<topic>` from `develop`. Do **not** merge into `develop` until announcement window is open and the wipe is approved.
3. **Otherwise?** -> feature branch from `develop`, PR into `develop`.

When a hotfix lands in `main`, immediately back-merge `main` into `develop`
so develop never trails on a fix that already shipped.

When a `release/wipe-*` branch is ready to ship, the merge order is:

```text
release/wipe-X -> develop -> main
```

Never merge `release/wipe-*` straight into `main`. The change must pass
through `develop` first so the next minor release contains it.

## Wipe-Risk Classification

Every PR description must carry a single line:

```text
Wipe-risk: NONE | DATA-MIGRATION | WIPE
```

| Label | Meaning | Examples |
|---|---|---|
| `NONE` | Pure content/balance/UI/fixes. Existing characters keep playing. | New monster, new item, new sprite, balance tuning, copy edits, refactors that do not touch persisted shapes. |
| `DATA-MIGRATION` | Persisted shape changes but a backward-compatible alembic/data backfill exists. Players keep their progress. | New nullable column with backfill, renamed field with compat alias, reorganised JSON section with one-time projection. |
| `WIPE` | Persisted shape changes are not safely migratable, or the design assumption behind existing data is gone. | Reworked attribute system, replaced inventory id scheme, restructured economy, switched skill progression formula, full rewrite (0.2 -> 0.3 style). |

Heuristic: if you cannot write a backward-compatible alembic migration with a
real `downgrade()` for the players you already have, it is `WIPE`. If you can
(however ugly), it is `DATA-MIGRATION`.

`NONE` may merge straight into `develop` or `hotfix/*` as usual.
`DATA-MIGRATION` requires an alembic revision and a working downgrade; check
the migration against a staging copy of prod data before merge.
`WIPE` may only land in `develop` after the announcement window has opened.

## Version Bumping Rules

Versions follow SemVer numerically but the meaning is fixed for this project:

| Change shape | Bump | Cadence | Source branch |
|---|---|---|---|
| Hotfix, security, regression, copy fix, single-flag rollout | `PATCH` (`0.3.0 -> 0.3.1`) | As needed, sometimes daily | `hotfix/*` -> `main` |
| New features, content, balance, refactors without persisted shape changes | `MINOR` (`0.3.x -> 0.4.0`) | Weekly train from `develop` -> `main` | `develop` -> `main` |
| Reworks that need a wipe, large architectural moves | `MINOR` with announcement | When announcement window closes | `release/wipe-*` -> `develop` -> `main` |
| Stage promotion (`alpha` -> `beta`, `beta` -> `release`) | Coincides with a `MINOR` or `MAJOR` tag | Once per stage | `develop` -> `main` |
| `1.0.0` itself | `MAJOR` | Once | `develop` -> `main` |

Stage label is bumped in `FrontendSettings.release_stage` (env override) at
the same time as the tag. It is not part of the version string.

Patch bumps do not need to wait for the weekly train.

## How to Route Work

When picking up a task, classify it once and route accordingly:

1. **What does the user want?** Phrase it as outcome, not diff. ("Add cooldown to shield bash" not "edit combat_resolver.py".)
2. **Is the bug in prod right now?** Yes -> `hotfix/*` from `main`. No -> step 3.
3. **Does it change persisted shapes?** No -> feature branch from `develop`. Yes -> step 4.
4. **Can backward-compat migration be written?** Yes -> `DATA-MIGRATION` on feature branch from `develop`. No -> `release/wipe-<topic>` from `develop`, plus a planned announcement (see below).

Record the choice in the PR description on the first line:

```text
Branch: hotfix | minor | wipe
Wipe-risk: NONE | DATA-MIGRATION | WIPE
Bump: patch | minor | major
```

## Wipe Announcement Protocol

When a `release/wipe-*` branch exists, before merging into `develop`:

1. Notice window opens. Minimum windows:
   - `alpha` stage: 7 days
   - `beta` stage: 30 days
   - `release` stage: wipes are not permitted; raise to the project owner.
2. Owner publishes a `/news` post titled e.g. `"Wipe on YYYY-MM-DD: <why>"`.
3. `release_progress_policy` on the landing remains unchanged (it is the standing rule); the news post is the specific instance.
4. After the wipe ships:
   - Add a footer entry to the affected `## [vX.Y.Z]` section in
     `docs/changelog/*.md`: `**Wipe.** <one sentence why>.`
   - Tag the commit with `v<X>.<Y>.<Z>` and a tag message that starts with `Wipe.`.

Do not skip the news post even if player count is low. The protocol is the
contract that makes the landing promise true.

## Git Tag and Image Convention

Production tags are exactly `v<X>.<Y>.<Z>`, no suffix. Pre-release builds may
use `v<X>.<Y>.<Z>-rc<N>` for explicit RCs but never appear in prod runtime.

`hatch-vcs` reads the tag at build time; no manual `version =` edit in
`pyproject.toml`.

`release_version` in `FrontendSettings` defaults to the latest released
version and is overridable per environment via `RELEASE_VERSION=`. Keep it in
sync with the tag at deploy time.

Image tags follow the deploy-management skill (release tag + commit SHA).

## Cross-Skill Contracts

When a change lands:

- The matching `docs/changelog/*.md` file gets an `Unreleased` line. Rules in `turnbasedmmorpg-changelog-release`.
- If the change is image-affecting, the deploy step follows `turnbasedmmorpg-deployment-management`.
- This skill owns the *branch and version decision*; the other two own *what to write and how to ship it*.

## Decision Self-Check

Before opening a PR, an agent must answer:

- What branch is this targeting and why?
- What is the wipe-risk label and the evidence for it?
- What version bump is implied?
- If `WIPE`, what is the announcement plan and which `/news` post covers it?
- Which changelog file received the `Unreleased` line?

Write the answers into the PR description verbatim. They are the audit trail.

## Common Mistakes

- Merging a `release/wipe-*` branch straight into `main` without going through `develop`.
- Treating any breaking-feeling change as `WIPE` when a migration is possible.
- Bumping `MAJOR` for an alpha or beta change. `1.0.0` is reserved for the release stage transition.
- Letting the stage drift on the landing while `release_version` stays the same after a stage promotion.
- Encoding the stage into the number (`0.x = alpha`). The stage is a separate signal.
- Forgetting the back-merge of `main` into `develop` after a hotfix.
- Shipping a wipe without a `/news` post, on the grounds that "no one will notice yet".
