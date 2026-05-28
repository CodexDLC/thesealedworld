---
name: turnbasedmmorpg-rift-design-gate
description: Rift design and implementation gate for TurnBasedMMORPG. Use before discussing, planning, documenting, designing, or implementing rifts, rift nodes, master nodes, rift movement, transition buttons, rift generation metadata, training rifts, rift backend/frontend routes, Redis/JSON prototypes, or any code under a future rift feature.
---

# TurnBasedMMORPG Rift Design Gate

## Purpose

Use this skill as the first guardrail for all rift work.

The rift system is under active design. Do not treat existing planning notes as
an implementation contract. The current goal is to build the shared language and
approved stages first, then expand this skill as real tasks and working code
stabilize.

## Read First

- `docs/agent-skills/turnbasedmmorpg-project/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-skill-builder/SKILL.md` when editing this skill
- `docs/planning/tasks/rift/approved_stages/README.md`
- `docs/planning/tasks/rift/transition_and_node_data_design.md`

For backend/API/service work, also read:

- `docs/agent-skills/turnbasedmmorpg-backend/SKILL.md`

For frontend/game UI work, also read:

- `docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md`
- `docs/agent-skills/turnbasedmmorpg-game-interface-design/SKILL.md`

## Source Priority

Use sources in this order:

1. Direct project-owner decisions in the current conversation.
2. `docs/planning/tasks/rift/approved_stages/`.
3. `docs/planning/tasks/rift/transition_and_node_data_design.md` as a working design base.
4. Other `docs/planning/tasks/rift/*` files only as idea drafts, not contracts.

If these sources conflict, pause and ask the project owner. Do not resolve the
conflict by inventing a permanent rule.

## Current Working Model

Rift work currently focuses on a pre-instance generation layer.

The important distinction:

- Master metadata and node metadata describe material used to generate a rift instance.
- They are not player runtime state, run progress, combat result state, or final persistence contracts.

Do not introduce runtime/run/progress concepts unless the owner explicitly asks
to design that layer.

## Master Metadata

Master metadata describes the broader generated zone language and generation
context. It may include:

- biome or semantic tags;
- the zone's general descriptive style;
- the opening/leading part of location descriptions;
- metadata for blocked passages, collapses, walls, unavailable directions, and similar obstacles;
- language resources used by generation and rendering;
- rules or metadata that allow the zone to expand.

This is generation metadata for future rift instances, not a live rift run.

## Node Metadata

Node metadata describes generated location-node material used by future rift
instances. It may include:

- node title;
- node-specific description details;
- data inserted into movement button templates;
- destination-driven transition wording data;
- template variables needed by the movement/transition renderer;
- node-specific suffixes or details for unavailable or blocked states.

The movement engine may own button templates, but the node owns the data used to
fill those templates.

## Transition Principle

Use destination-driven transitions as the working direction:

- Button text is assembled from the destination node's data.
- The engine owns reusable button templates.
- Nodes store the lexical/template data needed to make those buttons read correctly.
- Blocked or unavailable paths use master metadata plus node-specific data.

Do not reduce rift movement to exploration navigation. Rift movement is expected
to be its own layer because transitions can be symbolic, vertical, blocked,
destination-driven, or non-coordinate-like.

## Current Approved Stage

The first approved development stage is the local dev harness described in:

- `docs/planning/tasks/rift/approved_stages/phase_01_local_dev_harness.md`

For now, this means:

- use JSON on disk as a design/source fixture;
- do not create DB models or migrations;
- do not freeze final API contracts;
- keep local unauthenticated test surfaces explicitly dev-only;
- use Redis/runtime projection only if that stage decision is being worked on and the owner confirms the exact task.

## Hard Stops

Stop and ask before:

- creating rift DB models;
- creating Alembic migrations;
- creating shared DTOs or final API contracts;
- creating `src/backend/features/rift/` implementation files;
- choosing Redis key shapes;
- choosing how combat returns to rift;
- deciding contract-board behavior;
- deciding dirty loot behavior;
- treating planning notes as approved implementation steps;
- mixing generation metadata with live runtime/progress state.

## Editing Rule

Do not edit code for rifts unless the user explicitly asks with words such as:

- "пиши"
- "реализуй"
- "создай файл"
- "внеси правки"
- "сделай"
- "implement"
- "edit"

Discussion, design exploration, or statements like "надо делать" are not
permission to write code.

## Working Process

For rift design tasks:

1. Restate what layer is being discussed.
2. Separate owner-approved decisions from hypotheses.
3. Identify which metadata belongs to master and which belongs to node.
4. Identify what must remain out of scope for the current stage.
5. Update approved-stage task docs only when the owner asks to record a decision.
6. Update this skill only when a repeated rule has become stable enough to guide future agents.

## Current Status

This skill is an early base. It is intentionally not a final rift architecture
specification. Expand it as tasks are collected, decisions are confirmed, and
working code proves the shape of the system.
