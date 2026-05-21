# Modifiers Rules

This folder contains the reviewed modifier reference for combat actor math,
waterfall inputs, item affix contracts, and mapper responsibilities.

- [Modifier Vocabulary](./modifier_vocabulary.md)
- [Actor Mapper Reference](./actor_mapper_reference.md)
- Player-facing library article: [`library/rpg/modifiers.md`](../../library/rpg/modifiers.md)

Current runtime sources:

- `src/backend/features/character/dto/modifiers.py`
- `src/backend/features/character/runtime/combat_math_model.py`
- `src/backend/features/character/runtime/rules/attribute_modifiers.py`
- `src/backend/core/calculators/stats_waterfall_calculator.py`
- `src/backend/features/items/resources/modifier_contracts/`
- `src/backend/features/combat/runtime/engine/resolver.py`

The active DTO owner is the character feature DTO. Older shared modifier DTOs
may still exist for compatibility, but they are not the canonical place for new
modifier design.
