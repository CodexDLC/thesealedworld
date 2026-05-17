# Combat Contract Skill

This skill teaches agents where combat formulas belong, where snapshot mapping
belongs, and how to avoid duplicating resolver or waterfall work in catalogs or
actor builders.

Read this skill before touching:
- `src/backend/features/combat/runtime/engine/resolver.py`
- `src/backend/features/combat/runtime/engine/context_builder.py`
- `src/shared/schemas/modifier_dto.py`
- `src/backend/features/character/runtime/combat_math_model.py`
- `src/backend/features/monsters/runtime/combat_profile.py`
- `src/backend/core/calculators/stats_waterfall_calculator.py`

Also read:
- `docs/game-design/rpg-rules/Modifiers/Actor_Mapper_Contract.md`
- `docs/game-design/rpg-rules/Modifiers/Modifiers_Reference.md`

---

## Architecture Map — Who Owns What

```
Character / Monster builder
  combat_math_model.py         (CharacterCombatMathModelBuilder)
  combat_profile.py            (build_monster_combat_context)
        │
        │  writes raw.attributes and raw.modifiers
        │  each modifier: { base: float, source: {key: float}, temp: {} }
        ▼
StatsWaterfallCalculator
  src/backend/core/calculators/stats_waterfall_calculator.py
        │
        │  sums base + source values + temp values → flat ActorStats
        │  called once on session entry, then on dirty_stats after effect apply/remove
        ▼
ActorStats  (in-memory only, not persisted to Redis)
  .mods:   CombatModifiersDTO  ← flat floats, post-waterfall
  .skills: CombatSkillsDTO     ← flat floats, 0..1 scale
        │
        ▼
AbilityService / EffectService  (between Collector and Executor)
        │  applies ActiveEffectDTO to raw.modifiers.temp
        │  marks dirty_stats, triggers waterfall rebuild
        ▼
CombatResolver.resolve_exchange(atk_stats, def_stats, context)
        │  reads ONLY ActorStats.mods and ActorStats.skills
        │  no raw.modifiers access, no Redis, no DB
        ▼
InteractionResultDTO
```

---

## ActorSnapshot Contract

### What Must Be Populated BEFORE Any Exchange

| Snapshot Field | Populated By | Content |
|---|---|---|
| `meta.hp/en/tactics/tokens/feints` | Session/Lifecycle service | Current hot state |
| `raw.attributes` | Character/Monster builder | `{key: {base, source:{}, temp:{}}}` |
| `raw.modifiers` | Character/Monster builder | `{key: {base, source:{label:float}, temp:{}}}` |
| `skills` | Snapshot builder | `{skill_key: float}`, scale **0..1** |
| `loadout.layout` | Character/Monster builder | `{slot: skill_key, slot_trigger: trigger_id}` |
| `loadout.known_abilities` | Snapshot builder | `list[ability_id]` |
| `statuses.abilities/effects` | Combat runtime per round | ActiveAbilityDTO / ActiveEffectDTO |
| `stats` (ActorStats) | WaterfallCalculator | Rebuilt before each exchange if dirty |

### What Is Calculated INSIDE Resolver (Never Pre-Compute These)

- Accuracy roll: `(hand_accuracy + global_accuracy) * ctx.mods.accuracy_mult`
- Crit roll: `(hand_crit_chance + global_crit_chance) * (1.0 + skill_val)`
- Evasion check: `min(evasion - atk.anti_dodge_chance, dodge_cap)`
- Parry check: `min(parry * (1 + PARRY_SKILL_MULT_PER_POINT * skill_parrying), parry_cap)`
- Block check: `min(block * (1 + SHIELD_BLOCK_SKILL_MULT_PER_POINT * skill_parrying), shield_block_cap)`
- Counter check: `min(counter_attack_chance, counter_attack_cap)`
- Weapon damage: `rand((base + physical_damage + physical_damage_bonus)*(1-spread), ... ) - resist - armor`.
- Unarmed damage: `rand((strength_base * unarmed_efficiency + physical_damage_bonus)*(1-spread), ... ) - resist - armor`; unarmed does not add `physical_damage` twice.
- Healing: `rand(magical_damage*0.9, magical_damage*1.1) [* 1.5 if crit]`

---

## Loadout Layout Structure

```python
loadout.layout = {
    "main_hand":         "skill_swords",           # weapon mastery skill key
    "main_hand_trigger": "accuracy.true_strike",   # trigger ID: "section.field" or bare name
    "off_hand":          "skill_shield",            # or "skill_dual_wield" for a weapon
    "off_hand_trigger":  "crit.bleed_proc",
    "body":              "skill_heavy_armor",       # / skill_medium_armor / skill_light_armor
}
```

`ContextBuilder._analyze_intent()` reads `loadout.layout` to set `ctx.flags.meta.source_type`
and `ctx.flags.meta.weapon_class`. `ContextBuilder._analyze_defense()` reads `body` and
`off_hand` to set mastery flags.

Dual wield triggers when `source_type == "main_hand"` and `off_hand` is a non-shield skill.
Chance: `min(0.50, 0.25 + 0.25 * skill_dual_wield)` (normalized, no multiplier).

---

## Waterfall Layer Rules

| Layer | Rule | Examples |
|---|---|---|
| `base` | Systemic or attribute-derived intrinsic baseline; numeric | `evasion.base = agility * 0.05`; `main_hand_accuracy.base = 0.70` |
| `source` | Stable pre-combat: items, affixes, passives, equipment properties | `{"item:sword_01": 12.0}` |
| `temp` | Runtime: buffs, debuffs, stances, control, round-local mutations | Applied by EffectService, cleared on effect expiry |

Current state: mappers write plain floats into `source`. Operation strings (`+x`, `-x`, `*x`,
`=x`) described in `Actor_Mapper_Contract.md` are a planned enhancement — waterfall currently
treats source values as additive.

`temp` entries are written by `EffectService` using `ActiveEffectDTO.modified_keys` for
rollback. Waterfall is rebuilt after any temp change.

---

## Skill Scale

Skills in `ActorSnapshot.skills` and `ActorStats.skills` are **always 0..1 normalized**.

```python
skill_val = 0.0   # untrained
skill_val = 1.0   # fully trained (100%)
skill_val = 1.5   # overmastery via items/effects
```

UI display: `skill_val * 100` (as percent). Never divide by 100 in runtime math.

Correct usage in resolver:
```python
skill_multiplier = 1.0 + skill_val          # +100% at cap = 2× multiplier
chance = min(0.50, 0.25 + 0.25 * skill_dual_wield)  # 0.25 base, 0.50 at full mastery
```

---

## Offensive Branch Selection

`CombatResolver._get_offensive_val(stats, ctx, key)` dispatches on `ctx.flags.meta.source_type`:

| source_type | damage_base | accuracy | armor_penetration_pct | crit_chance |
|---|---|---|---|---|
| `main_hand` | `main_hand_damage_base` | `main_hand_accuracy + accuracy` | `main_hand_armor_penetration_pct + armor_penetration_pct` | `main_hand_crit_chance + crit_chance` |
| `off_hand` | `off_hand_damage_base` | `off_hand_accuracy + accuracy` | `off_hand_armor_penetration_pct + armor_penetration_pct` | `off_hand_crit_chance + crit_chance` |
| `magic` | `magical_damage` | `magical_accuracy + accuracy` | `0.0` | `magical_crit_chance` (no global crit) |
| `item` | `item_damage_base` | `item_accuracy` | `item_armor_penetration_pct + armor_penetration_pct` | `item_crit_chance` |

`ContextBuilder._analyze_intent()` sets `source_type`:
- `strategy == "instant"` → `"magic"`
- `strategy == "item"` → `"item"`
- `strategy == "exchange"` → `"main_hand"` or `"off_hand"` from `external_mods.hand`

---

## Resolver Dependency Table

| Resolver reads | ActorStats path | Populated by | Status |
|---|---|---|---|
| accuracy (main) | `atk.mods.main_hand_accuracy + atk.mods.accuracy` | CharMathModel / MonsterProfile | OK |
| accuracy (off) | `atk.mods.off_hand_accuracy + atk.mods.accuracy` | CharMathModel / MonsterProfile | OK |
| accuracy (magic) | `atk.mods.magical_accuracy + atk.mods.accuracy` | CharMathModel / MonsterProfile | OK |
| damage_base (main) | `atk.mods.main_hand_damage_base` | CharMathModel / MonsterProfile | OK |
| damage_base (off) | `atk.mods.off_hand_damage_base` | CharMathModel / MonsterProfile | OK |
| damage_base (magic) | `atk.mods.magical_damage` | CharMathModel / MonsterProfile | OK |
| damage_spread (main/off/magic) | `atk.mods.{prefix}_damage_spread` | CharMathModel / MonsterProfile | OK |
| physical_suppression | `atk.mods.physical_suppression` | CharMathModel | OK |
| armor_penetration_pct (main/off/item) | `atk.mods.{source}_armor_penetration_pct + armor_penetration_pct` | CharMathModel | OK |
| armor_ignore_chance (main/off/item) | `atk.mods.{source}_armor_ignore_chance + armor_ignore_chance` | CharMathModel | OK |
| magical_penetration (magic/elemental) | `atk.mods.magical_penetration` | CharMathModel | OK |
| crit_chance (main/off) | `atk.mods.{prefix}_crit_chance + crit_chance` | CharMathModel | OK |
| crit_chance (magic) | `atk.mods.magical_crit_chance` only | CharMathModel | OK (asymmetric) |
| crit_cap (all) | `atk.mods.{prefix}_crit_cap` | DTO defaults | OK |
| physical_damage | `atk.mods.physical_damage` for non-unarmed physical attacks | Waterfall from Strength | OK |
| physical_damage_bonus | `atk.mods.physical_damage_bonus` | CharMathModel | OK |
| evasion | `def.mods.evasion` | CharMathModel / MonsterProfile | OK |
| dodge_cap | `def.mods.dodge_cap` (default 0.75) | DTO default | OK |
| anti_dodge_chance | `atk.mods.anti_dodge_chance` | CharMathModel | OK |
| parry | `def.mods.parry` | CharMathModel | OK |
| parry_cap | `def.mods.parry_cap` (default 0.50) | DTO default | OK |
| block | `def.mods.block` | CharMathModel | OK |
| shield_block_cap | `def.mods.shield_block_cap` (default 0.75) | DTO default | OK |
| physical_resistance | `def.mods.physical_resistance` | CharMathModel / MonsterProfile | OK |
| armor | `def.mods.armor` | CharMathModel / MonsterProfile | OK |
| `{elem}_resistance` | `def.mods.{elem}_resistance` | CharMathModel / MonsterProfile | OK |
| magical_penetration (elemental) | `atk.mods.magical_penetration` | CharMathModel | OK |
| counter_attack_chance | `def.mods.counter_attack_chance` | CharMathModel | OK |
| counter_attack_cap | `def.mods.counter_attack_cap` (default 0.50) | DTO default | OK |
| skill_light/medium/heavy_armor | `def.skills.skill_{type}_armor` | Snapshot skills | OK |
| skill_{weapon_class} (crit mult) | `atk.skills.skill_{class}` | Snapshot skills | OK (formula bug) |
| healing base | `atk.mods.magical_damage` | CharMathModel | OK |

---

## Caps Table

| Field | DTO Default | Applied In |
|---|---|---|
| `dodge_cap` | 0.75 | `resolver._step_evasion_roll` |
| `parry_cap` | 0.50 | `resolver._step_parry_roll` |
| `shield_block_cap` | 0.75 | `resolver._step_block_roll` |
| `counter_attack_cap` | 0.50 | `resolver._step_counter_check` |
| `resistance_cap` | 0.85 | NOT in resolver — pending waterfall layer |
| `vampiric_trigger_cap` | 1.0 | NOT in resolver — trigger-driven, pending |
| `main_hand_crit_cap` | **MISSING from DTO** | Returns 0.0 — crits blocked in normal flow |
| `off_hand_crit_cap` | **MISSING from DTO** | Returns 0.0 — crits blocked in normal flow |
| `magical_crit_cap` | **MISSING from DTO** | Returns 0.0 — crits blocked in normal flow |

---

## Modifier Key Status

### Active — Used by Resolver

```
main_hand_damage_base    main_hand_damage_spread    main_hand_accuracy
main_hand_crit_chance    main_hand_armor_penetration_pct
main_hand_armor_ignore_chance
off_hand_damage_base     off_hand_damage_spread     off_hand_accuracy
off_hand_crit_chance     off_hand_armor_penetration_pct
off_hand_armor_ignore_chance
item_damage_base         item_accuracy              item_crit_chance
item_armor_penetration_pct item_armor_ignore_chance
magical_damage           magical_damage_spread      magical_accuracy
magical_crit_chance      magical_penetration
accuracy                 crit_chance                physical_suppression
armor_penetration_pct    armor_penetration_flat     armor_ignore_chance
physical_damage_bonus
evasion                  dodge_cap                  anti_dodge_chance
parry                    parry_cap
block                    shield_block_cap
physical_resistance      armor
{fire|water|air|earth|light|dark|arcane|nature}_resistance
counter_attack_chance    counter_attack_cap
```

### Pending — In DTO, Not Yet Applied by Resolver

```
main_hand_crit_cap       off_hand_crit_cap          magical_crit_cap
resistance_cap           vampiric_trigger_cap
main_hand_damage_bonus   off_hand_damage_bonus
healing_power            received_healing_bonus
{elem}_damage_bonus                                   (elemental attack bonus, pending)
item_damage_bonus
```

### Renamed (Aliases Active in Both Mappers)

```
dodge_chance       → evasion
parry_chance       → parry
shield_block_chance → block
damage_reduction_flat → armor
magical_damage_base   → magical_damage    (Modifiers_Reference.md uses old name)
magical_resistance    → magic_resist
```

---

## Unarmed / Strength Interaction

Strength flows into `physical_damage` through the attribute waterfall. For weapon attacks,
resolver adds that value to the hand damage base according to `Attributes/README.md`.
For unarmed attacks, the mapper already uses Strength as `main_hand_damage_base`, so
resolver skips the extra `physical_damage` addition to avoid double counting and applies
the `skill_unarmed` efficiency curve instead.

```python
# CharacterCombatMathModelBuilder._apply_unarmed_base:
main_hand_damage_base.base = strength           # strength value
main_hand_damage_spread.base = 0.50             # 50% spread
main_hand_accuracy.base = 0.70                  # same as weapon base
```

Unarmed resolver curve:

```python
efficiency = 0.5 + (2.5 * skill_unarmed)        # 0.5x -> 3.0x
spread = max(0.10, 0.50 - (0.40 * skill_unarmed))
```

---

## Temp Effects, Buffs, Debuffs

Temp state is in `ActorSnapshot.statuses`:
- `ActiveAbilityDTO` — stances, channeling; stores `modified_keys: list[str]` for rollback
- `ActiveEffectDTO` — buffs, debuffs, control; stores `modified_keys` and `impact`

EffectService writes to `raw.modifiers[key]["temp"][effect_uid]`. After write it sets
`dirty_stats` and calls WaterfallCalculator to rebuild `ActorStats`. Resolver never reads
raw.modifiers directly — it always works with already-rebuilt stats.

Round-local mutations from triggers (via `_apply_mutation`) write to `ctx.flags`, `ctx.mods`,
or `ctx.stages` — these are pipeline-local and do NOT persist to the snapshot.

---

## Known Bugs (Not Fixed Here — Track Separately)

| # | Location | Bug | Fix |
|---|---|---|---|
| 1 | Item damage contract | Item branch exists in resolver, but item abilities still need end-to-end gameplay tuning | Add item-use balance tests and catalog examples |

---

## Common Mistakes Agents Make

**DO NOT duplicate resolver math in mappers.**
Wrong: computing `base = 0.70 - 0.08 + 0.04 = 0.66` and writing it to `base`.
Correct: write `base = 0.70`, source `{"item:sword:penalty": -0.08, "skill:polearms:refund": +0.04}`.

**DO NOT pre-apply parry/block skill bonuses in mappers.**
Parry and shield block base chances come from equipment. `CombatResolver` applies
the normalized `skill_parrying` multiplier during the exchange.

**DO NOT write attributes into modifiers.**
Strength goes into `raw.attributes.strength`. WaterfallCalculator derives
`physical_damage` from it. Mappers put strength directly into
`main_hand_damage_base` only for unarmed.

**DO NOT assume skills are 0..100.**
`actor.skills["skill_swords"] = 0.75` means 75% mastery. Use directly: `1.0 + skill_val`.

**DO NOT read `raw.modifiers` in resolver.**
Resolver input is `ActorStats`, not `ActorSnapshot`. If you need a modifier in
resolver, it must flow through: mapper → waterfall → ActorStats.mods.

**DO NOT write temp state into resolver.**
`_apply_mutation` writes to `ctx.flags` / `ctx.mods` (pipeline context), not to
`actor.raw.modifiers`. Those go through EffectService with rollback support.

---

## Verification Commands

Run before declaring combat contract work complete:

```powershell
# Unit tests for combat runtime
python -m pytest tests/backend/features/combat/ -v

# Character snapshot / math model
python -m pytest tests/backend/features/character/runtime/ -v

# Monster combat profile
python -m pytest tests/backend/features/monsters/runtime/ -v

# Full backend fast check
python -m pytest tests/backend/ -x -q
```

Key test files:
- [`tests/backend/features/combat/test_runtime_processors.py`](../../../tests/backend/features/combat/test_runtime_processors.py) — executor, damage, death, feints
- [`tests/backend/features/character/runtime/test_combat_math_model.py`](../../../tests/backend/features/character/runtime/test_combat_math_model.py) — modifier keys, unarmed, shield mastery
- [`tests/backend/features/character/runtime/test_attribute_modifiers.py`](../../../tests/backend/features/character/runtime/test_attribute_modifiers.py) — waterfall from attributes
- [`tests/backend/features/monsters/runtime/test_registry_and_combat_profile.py`](../../../tests/backend/features/monsters/runtime/test_registry_and_combat_profile.py) — humanoid loadout resolution
