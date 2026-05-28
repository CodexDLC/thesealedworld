# 04. Temporary Blocker Resolution

Status: dev scaffold implemented.

## Goal

Allow `blocked_temporary` passage edges to be opened or failed through character capabilities.

## Action Layer Decision

Rift interactions should not grow one public route per interaction type.

The frontend-facing split is:

- movement/init routes own travel and ticking;
- one action route owns rift interactions and routes by `action_type`;
- finalization/exit can later become an action type unless it needs a dedicated lifecycle boundary.

Current action endpoint:

```text
POST /api/dev/rift/{rift_instance_id}/action
POST /game/rift/action
```

Current action types:

- `resolve_transition_combat`
- `resolve_node_event`
- `resolve_blocker`

## Current Blocker Contract

Temporary blockers already return:

- `state: blocked_temporary`
- `action: inspect_blocker`
- `is_active: true`
- `target_node_id`
- `blocker_key`
- one generated attribute check under `requirement.check`
- `requirement_label` for player-facing button text

Button labels should show the required capability directly, for example:

- `Открыть решетку (Сила 15)`
- `Открыть решетку (Интеллект 15)`
- `Открыть решетку (Ловкость 15)`

Example requirement:

```json
{
  "type": "skill_or_attribute_check",
  "mode": "single_attribute",
  "check": {
    "kind": "attribute",
    "key": "intelligence",
    "dc": 15,
    "label": "Понять механизм"
  },
  "status": "contract_only"
}
```

## Current Dev Implementation

`resolve_blocker` validates the current edge, reads the edge requirement, checks a dev attribute context or action payload, and then:

- on success, mutates both edge directions from `blocked_temporary` to `open`;
- on failure, keeps the edge closed;
- returns a fresh rift screen through the common action response.

This is not a resource-consuming action:

- no resource cost;
- no special time cost;
- no limited attempts;
- no permanent failure state;
- the passage opens if the player or future group has the required capability.

For future group rifts, the capability check should be satisfiable by any eligible group member, and the opened passage state is shared for the run/group instance.

Dev action context exists only for local testing and must live as a resource snapshot, not as hardcoded code or setting DNA.

Current file:

```text
src/backend/features/rift/resources/json/starter_rift/dev_character.json
```

Current snapshot attributes:

```json
{
  "character": {
    "attributes": {
      "strength": 14,
      "intelligence": 16,
      "dexterity": 12
    }
  }
}
```

Because each blocker gets only one generated check, some blockers pass with this context and some fail.

## Future Capability Resolution

The dev attribute context must later be replaced by real capability providers:

- active character attributes;
- skills;
- items/tools;
- party/group member contribution if group rifts use shared action resolution.

Open questions before real integration:

- Which service owns character capability checks?
- How should group capability providers report which member opened the path?

## Exit Criteria

- Frontend can click blocker actions through the common action route.
- Backend returns success/failure result.
- Opened blocker changes movement button into normal movement.
