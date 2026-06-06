---
name: turnbasedmmorpg-changelog-release
description: Changelog and release-note discipline for The Sealed World. Use when preparing code commits, updating changelogs, creating release tags, summarizing changes between versions, or touching CHANGELOG.md or docs/changelog/.
---

# TurnBasedMMORPG Changelog Release

## Purpose

Keep changelog work useful for a private MVP product.

During development between tags, record each meaningful commit/change as a short
`Unreleased` line. Before creating a release tag, collapse that accumulated list
into a compact, readable release summary.

## Read First

- `CHANGELOG.md`
- `docs/changelog/backend.md`
- `docs/changelog/frontend-site.md`
- `docs/changelog/frontend-game-client.md`
- `docs/agent-skills/turnbasedmmorpg-release-flow/SKILL.md` for the branch + version + wipe-risk decision that drives which entries get summarised and what version number to bump to.
- `docs/agent-skills/turnbasedmmorpg-deployment-management/SKILL.md` when the work affects release, deploy, images, tags, or CI/CD.

## Commit-Time Rule

When preparing a commit that changes code, contracts, runtime behavior, deploy,
or user-facing UI, add a short line under `## [Unreleased]` in the matching
layer file:

- Backend/game runtime -> `docs/changelog/backend.md`
- Public site/auth/account/cabinet/library -> `docs/changelog/frontend-site.md`
- Gameplay browser client -> `docs/changelog/frontend-game-client.md`
- Cross-layer release/deploy/product baseline -> `CHANGELOG.md` plus the affected layer file

Write changelog entries as concise outcome statements, not raw file lists.
One line is usually enough; a few words are acceptable when the change is small
but still meaningful.

Good:

```text
- Game lobby selection now issues character-scoped game tokens through the backend service boundary.
- Env setup now includes production template and secret generator.
```

Avoid:

```text
- Edited router.py, service.py, tests, and template.html.
```

Do not skip meaningful work just because it is small. Do skip trivial formatting,
typo-only docs edits, test-only renames, or mechanical cleanup that has no
product/runtime/architecture meaning.

The `Unreleased` list is allowed to be more granular than a final release note.
It is the working memory between tags.

## Tag-Time Rule

When creating or preparing a release tag:

1. Inspect changes since the previous tag:

```powershell
git describe --tags --abbrev=0
git log --oneline <previous-tag>..HEAD
git diff --stat <previous-tag>..HEAD
```

If there is no previous tag, treat `v0.0.0` as the MVP baseline.

2. Read every `## [Unreleased]` section in root and layer changelogs.
3. Collapse the granular entries into meaningful release stages for the new
   version: product, architecture, backend, site, game client, deploy, docs, or
   known limitations as applicable.
4. Move the compact summary under the new version heading.
5. Start a fresh empty `## [Unreleased]` section at the top.
6. Keep the root section compact: product changes, architecture changes, release
   and deploy changes, and major known limitations.
7. Keep detailed layer summaries in `docs/changelog/`; do not paste a long
   commit list into the root changelog.
8. Use version headings like:

```markdown
## [v0.0.0] - MVP Baseline
```

## Release Versioning

Package versions come from git tags through `hatch-vcs`.

- Tag `v0.0.0` produces package version `0.0.0`.
- Dev builds without a tag may produce a `.devN` version.
- Do not manually edit `version = ...` in `pyproject.toml`; the project uses
  `dynamic = ["version"]`.

## Final Self-Check

Before reporting commit or release prep as done, state:

- which changelog file received the `Unreleased` marker;
- whether the root changelog was updated or intentionally left unchanged;
- for tag prep, what previous tag range was summarized.
