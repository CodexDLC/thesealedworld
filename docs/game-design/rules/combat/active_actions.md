# Active Combat Actions

Status: design reference, not final runtime contract.

This file records the current design split between active combat action types.
Final UI naming can change after the combat interface and ability system are
designed.

## Action Types

### Basic Attack Or Exchange

The baseline combat action is an attack or exchange.

It represents the normal weapon/body clash driven by equipment, combat stats,
weapon mastery, tactical style, armor, and defender reactions.

Current combat runtime already has basic exchange catalog resources and combat
text around weapon classes, hits, crits, misses, dodge, parry, and block.

### Combat Technique Or Feint

Working player-facing name: **combat technique (feint)**.

This is a physical or tactical action based on skill, timing, stance, position,
and combat rhythm. It is not a Gift and does not release Symbiote rift energy as
its primary source.

The final player-facing word is not locked. Possible names include:

- feint;
- combat technique;
- maneuver;
- tactical action;
- dance step or rhythm term if the combat UX moves in that direction.

Design intent:

- uses combat/tactical resources rather than Gift tokens;
- is unlocked or improved by skills, weapon identity, armor style, or combat
  state;
- can modify an exchange, prepare a reaction, create pressure, or change tempo.

### Gift Ability

A Gift ability is a conscious release of accumulated rift energy through the
Symbiote.

For the player it can look like familiar magic: fire, light, darkness, healing,
shielding, poison, movement, roots, curses, or body enhancement. In system
logic, it is an energy construct shaped by the Symbiote and the active Gift.

Design intent:

- uses Energy as cost;
- uses Gift tokens as combat charge or rhythm;
- belongs to the Symbiote/Gift progression branch;
- can be active, passive, reactive, sustained, or rank-scaled in future systems.

## Chaining And Instant Actions

The old design direction allowed some abilities to be used without ending the
normal exchange and to chain several actions while resources are available.

Keep this as future design direction only. Do not treat it as current runtime
truth until the ability runtime, initiative rules, UI flow, and resource
spending model are reviewed against code.

## Current Runtime Pointers

Relevant current code surfaces:

```text
src/backend/features/game_catalog/combat/resources/basic_exchanges/
src/backend/features/game_catalog/combat/resources/feints/
src/backend/features/game_catalog/combat/resources/abilities/
src/backend/features/game_catalog/combat/resources/gifts/
```

The current ability catalog contains early/debug-style Gift abilities. Do not
use those entries as the final Gift ability design source.
