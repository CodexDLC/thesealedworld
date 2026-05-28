# 09. Final Feature Refactor

Status: planned.

## Goal

After the mechanics are proven, refactor the rift feature into the final backend structure.

## Scope

- Move prototype resources/services/runtime code into the agreed feature layout.
- Separate API, service, runtime, generation, events and integrations.
- Remove temporary dev-only shortcuts that are no longer needed.
- Keep a controlled dev harness for testing rifts without full game flow.

## Dependencies

This task should happen after:

- travel/tick runtime;
- transition combat;
- node entry event resolver;
- temporary blocker resolution;
- persistence model decisions;
- zone instance/meta contract.

## Exit Criteria

- Feature layout is stable.
- Tests cover final contracts.
- Prototype-only structure is removed or explicitly marked as dev harness.
