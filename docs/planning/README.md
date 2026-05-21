# Planning

This directory is the working planning area for future development. It is not
the stable runtime documentation layer.

## Folders

- `roadmap/` - longer product and engineering directions, grouped by theme or
  milestone.
- `tasks/` - temporary task documents for work that is expected, queued, or in
  progress.
- `ideas/` - raw ideas that still need design review before becoming roadmap or
  tasks.
- `tech-debt/` - refactor backlog, audits, cleanup plans, and post-MVP technical
  improvements.

## Task Lifecycle

Task documents are temporary. When a task is completed:

1. Update the stable documentation in `docs/ru/` that describes the implemented
   behavior.
2. Update the appropriate changelog.
3. Add or update public news/devlog content when the change is player-facing.
4. Remove the task document.

Do not keep completed task files as a permanent archive. Git history and
changelogs carry that history.

## Stable Documentation Boundary

- `docs/ru/` is the only stable collected documentation layer for current
  implemented behavior and architecture.
- `docs/game-design/` describes game design, lore, mechanics intent, and product
  design canon.
- `docs/planning/` describes future, expected, or in-progress work.
