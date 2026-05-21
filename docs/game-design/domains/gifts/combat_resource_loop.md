# Combat Resource Loop

Gift combat uses two resource concepts:

- Energy is the cost paid to use Gift abilities.
- Gift tokens are the combat charge or rhythm resource for Gift abilities.

## Token Generation

Gift tokens are expected to accumulate during combat exchanges.

The exact generation formula is not finalized, but the design intent is that
every exchange can move the player closer to using Gift abilities. Different
Gifts, ranks, passives, statuses, or build choices may later modify token gain.

## Spending Pattern

The player can choose different spending tempos:

- spend tokens as soon as enough are available;
- save tokens for a stronger sequence later;
- spend several abilities in a row after building resources;
- build around fast generation and frequent smaller uses;
- build around delayed burst windows.

This creates a separate tactical layer beside normal skill-driven combat.

## Energy Cost

Energy is the cost gate. Gift tokens represent combat readiness, but the player
still needs enough Energy to activate the ability.

This allows future abilities to vary by:

- high token, low Energy cost;
- low token, high Energy cost;
- sustained passive drain;
- burst usage;
- defensive emergency cost;
- rank-scaled cost or efficiency.

## Design Status

Gift tokens and Energy are active design concepts. Exact DTOs, runtime storage,
UI display, balancing constants, and resolver integration are future
implementation tasks.
