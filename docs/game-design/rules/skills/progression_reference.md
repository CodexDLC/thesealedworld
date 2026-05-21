# Skill Progression Reference

Status: current runtime formula with alpha tuning notes.

Code source:

```text
src/backend/core/calculators/skill_progression_calculator.py
```

## Design Intent

Skills grow through use.

Each action can award growth to one or more skills. Growth is faster when the
character has strong supporting attributes and slower when the current skill
value is already high.

This creates the intended shape:

- early training is visible;
- high mastery slows down;
- attribute weights influence learning pressure;
- different skills can grow at different rates through `rate_mod` and
  `wall_mod`.

Future systems may allow skill training through trainers, halls, or offline/AFK
practice loops. That belongs to skill progression only. Symbiote progression is
a separate scale and should use intent-driven experience sources rather than
passive skill training.

## Runtime Scale

Runtime skill values are normalized floats.

```text
0.0 = untrained
1.0 = full baseline mastery
>1.0 = possible overmastery from future items/effects/systems
```

UI may display this as `0..100`.

Do not divide runtime skill values by `100` in combat or progression formulas.

## Runtime Formula

Current runtime constants:

```text
GLOBAL_BASE_RATE = 0.00005
GLOBAL_BASE_WALL = 100.0
```

`GLOBAL_BASE_RATE` is currently tuned for alpha speed. It is a runtime constant,
not final balance canon.

For each skill progression entry:

```text
base_power = sum(attribute_value * skill_stat_weight) * action_power
effective_wall = GLOBAL_BASE_WALL * wall_mod
resistance = 1 + current_skill * effective_wall
delta = (base_power * GLOBAL_BASE_RATE * rate_mod) / resistance
```

If `base_power` is supplied explicitly, it replaces the weighted attribute sum
and is still multiplied by `action_power`.

## Inputs

Each progression entry can include:

- skill definition;
- current attributes;
- current skill value;
- action power;
- optional explicit base power;
- optional `rate_mod`;
- optional `wall_mod`.

The skill definition supplies:

- `stat_weights`;
- `rate_mod`;
- `wall_mod`.

## Alpha Tuning

The current alpha progression rate is intentionally faster than a final
long-term economy may need.

When balancing after playtests, preserve the formula shape unless there is a
clear design reason to change it. Prefer tuning constants and per-skill
modifiers before replacing the progression model.

## Future Documentation Boundary

This file explains progression math and design intent.

The full skill catalog contract, DTO fields, surface contracts, and service API
belong in stable implementation docs under `docs/ru` when that domain is
reviewed against code.
