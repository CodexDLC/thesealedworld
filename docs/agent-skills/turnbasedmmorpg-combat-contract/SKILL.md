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
- `docs/game-design/rules/modifiers/actor_mapper_reference.md`
- `docs/game-design/rules/modifiers/modifier_vocabulary.md`

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
        │  sums base + source values + temp values → flat modifier values
        ▼
BasePowerAssembler
  src/backend/features/combat/runtime/engine/base_power_assembler.py
        │
        │  turns weapon power + weighted stat power + mastery into final hand base
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

- Accuracy roll: `(0.70 + min(skill_val, 1.0) * 0.30 + source_accuracy_modifier) * ctx.mods.accuracy_mult`, clamped to `0..1`
- Crit roll: `(hand_crit_chance + global_crit_chance) * (1.0 + skill_val)`
- Evasion check: `min(evasion - atk.anti_dodge_chance, dodge_cap)`
- Parry check: `min(parry * (1 + PARRY_SKILL_MULT_PER_POINT * skill_parrying), parry_cap)`
- Shield block check: `min((block + SHIELD_BLOCK_SKILL_BONUS_AT_FULL * skill_shield_mastery) * shield_block_chance_mult, shield_block_cap)`.
  A successful shield block is a shield-contact event, not full damage cancel:
  it rolls the item's defensive/counter weights, then either adds
  `shield_guard_power` to mitigation or reflects shield power.
  Shield formula flags may force the defensive branch, force the counter branch,
  invert branch weights, or make counter reflect from shield contact power.
- Counter check: `min(counter_attack_chance, counter_attack_cap)`
- Weapon damage: `rand((assembled_base + physical_damage_bonus)*(1-spread), ... ) - resist - armor`.
- Elemental/magic damage: `rand(magical_damage*(1-spread), ...) - elemental_resist - magic_armor`.
- Assembled weapon base: `weapon_power + ((strength_power*wS + agility_power*wA) * mastery_factor)`.
  Weapon classes use normalized two-stat damage weights; `endurance` does not feed ordinary weapon damage.
- Unarmed damage: `rand((strength_base * unarmed_efficiency + physical_damage_bonus)*(1-spread), ... ) - resist - armor`; unarmed does not add `physical_damage` twice.
- Healing: `rand(magical_damage*0.9, magical_damage*1.1) [* 1.5 if crit]`

Mass-target feints use the normal resolver for every concrete target. The
primary target is the exchange target; secondary targets are executor-created
`unidirectional` interactions with `feint_role="secondary"`, `pay_cost=False`,
and `generate_feints=False`. They keep physical hit/defense/armor checks but do
not advance exchange counters, do not return target-queue pairs, and do not
create counter/off-hand chain tasks.

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
| `base` | Systemic or attribute-derived intrinsic baseline; numeric | `evasion.base = agility * 0.05`; hand accuracy bases stay `0.0` because hit baseline is resolver-owned |
| `source` | Stable pre-combat: items, affixes, passives, equipment properties | `{"item:sword_01": 12.0}` |
| `temp` | Runtime: buffs, debuffs, stances, control, round-local mutations | Applied by EffectService, cleared on effect expiry |

Current state: mapper sources can be plain numeric additive values or operation
commands such as `+x`, `-x`, `*x`, `/x`, and `=x`. Compiled item modifier
contracts can emit operation commands; older or direct mapper values may still
be plain numeric additions.

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

`resolver.support.offensive_lookup.get_offensive_val(stats, ctx, key)` dispatches on `ctx.flags.meta.source_type`:

| source_type | damage_base | accuracy | armor_penetration_pct | crit_chance |
|---|---|---|---|---|
| `main_hand` | `main_hand_damage_base` | `0.70 + skill_bonus + main_hand_accuracy + accuracy` | `main_hand_armor_penetration_pct + armor_penetration_pct` | `main_hand_crit_chance + crit_chance` |
| `off_hand` | `off_hand_damage_base` | `0.70 + skill_bonus + off_hand_accuracy + accuracy` | `off_hand_armor_penetration_pct + armor_penetration_pct` | `off_hand_crit_chance + crit_chance` |
| `magic` | `magical_damage` | `0.70 + skill_bonus + magical_accuracy + accuracy` | `0.0` | `magical_crit_chance` (no global crit) |
| `item` | `item_damage_base` | `0.70 + skill_bonus + item_accuracy` | `item_armor_penetration_pct + armor_penetration_pct` | `item_crit_chance` |

`ContextBuilder._analyze_intent()` sets `source_type`:
- `strategy == "instant"` → `"magic"`
- `strategy == "item"` → `"item"`
- `strategy == "exchange"` → `"main_hand"` or `"off_hand"` from `external_mods.hand`

---

## Resolver Dependency Table

| Resolver reads | ActorStats path | Populated by | Status |
|---|---|---|---|
| accuracy (main) | `0.70 + weapon skill bonus + atk.mods.main_hand_accuracy + atk.mods.accuracy` | Resolver + CharMathModel / MonsterProfile modifiers | OK |
| accuracy (off) | `0.70 + weapon skill bonus + atk.mods.off_hand_accuracy + atk.mods.accuracy` | Resolver + CharMathModel / MonsterProfile modifiers | OK |
| accuracy (magic) | `0.70 + skill bonus + atk.mods.magical_accuracy + atk.mods.accuracy` | Resolver + CharMathModel / MonsterProfile modifiers | OK |
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
| physical_strength_power | `atk.mods.physical_strength_power` for weapon/style assembly | Waterfall from Strength | OK |
| physical_agility_power | `atk.mods.physical_agility_power` for weapon assembly | Waterfall from Agility | OK |
| physical_endurance_power | `atk.mods.physical_endurance_power` for style-specific assembly, not ordinary weapon damage | Waterfall from Endurance | OK |
| physical_damage | legacy/reserved flat field; weapon resolver does not add it automatically | DTO / compatibility | OK |
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
| magic_armor | `def.mods.magic_armor` | CharMathModel jewelry power / MonsterProfile | OK |
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
| `main_hand_crit_cap` | 0.75 | `resolver._step_critical_roll` |
| `off_hand_crit_cap` | 0.75 | `resolver._step_critical_roll` |
| `magical_crit_cap` | 0.75 | `resolver._step_critical_roll` |

---

## Modifier Key Status

### Active — Used by Resolver Or Base-Power Assembly

```
main_hand_damage_base    main_hand_damage_spread    main_hand_weapon_power
main_hand_stat_damage_raw main_hand_stat_damage_effective main_hand_mastery_factor
main_hand_damage_spread_raw main_hand_accuracy
main_hand_crit_chance    main_hand_armor_penetration_pct
main_hand_armor_ignore_chance
off_hand_damage_base     off_hand_damage_spread     off_hand_weapon_power
off_hand_stat_damage_raw off_hand_stat_damage_effective off_hand_mastery_factor
off_hand_damage_spread_raw off_hand_accuracy
off_hand_crit_chance     off_hand_armor_penetration_pct
off_hand_armor_ignore_chance
item_damage_base         item_accuracy              item_crit_chance
item_armor_penetration_pct item_armor_ignore_chance
magical_damage           magical_damage_spread      magical_accuracy
magical_crit_chance      magical_penetration
accuracy                 crit_chance                physical_suppression
armor_penetration_pct    armor_penetration_flat     armor_ignore_chance
physical_strength_power  physical_agility_power     physical_endurance_power
physical_damage_bonus
evasion                  dodge_cap                  anti_dodge_chance
parry                    parry_cap
block                    shield_block_cap
physical_resistance      armor                    magic_armor
shield_guard_power
shield_style_guard_power_raw shield_style_guard_power_bonus
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
magical_armor        → magic_armor
magical_damage_base   → magical_damage    (old design docs used this name)
magical_resistance    → magic_resist
```

---

## Unarmed / Strength Interaction

Strength flows into `physical_strength_power` through the attribute waterfall.
Agility and Endurance flow into their own physical power fields. For weapon
attacks, `BasePowerAssembler` combines weapon power, class-specific normalized
two-stat damage weights, and weapon mastery into the final hand damage base
before `ActorStats` is created. The current weapon damage table uses Strength
and Agility only; Endurance is reserved for survival and style-specific
mechanics such as shield guard power. The resolver reads that assembled base
and does not add `physical_damage`.

For unarmed attacks, the mapper already uses Strength as `main_hand_damage_base`,
so `BasePowerAssembler` skips the `unarmed` class and the resolver applies the
`skill_unarmed` efficiency curve.

```python
# CharacterCombatMathModelBuilder._apply_unarmed_base:
main_hand_damage_base.base = strength           # strength value
main_hand_damage_spread.base = 0.50             # 50% spread
main_hand_accuracy.base = 0.0                   # hit baseline lives in resolver
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
Wrong: computing `base = 0.70 + 0.30 * skill - 0.10` and writing it to `main_hand_accuracy.base`.
Correct: keep hand accuracy as modifier-only and let resolver combine built-in base, skill bonus, and sources.

**DO NOT pre-apply parry/block skill bonuses in mappers.**
Parry and shield block base chances come from equipment. `CombatResolver`
applies `skill_parrying` to parry and `skill_shield_mastery` to shield block
during the exchange.

**DO NOT write attributes into modifiers.**
Strength, Agility, and Endurance go into `raw.attributes`. WaterfallCalculator
derives `physical_strength_power`, `physical_agility_power`, and
`physical_endurance_power`; `BasePowerAssembler` uses Strength/Agility for
ordinary weapon damage and may use Endurance only for style-specific mechanics
such as shield guard scaling. Mappers put strength directly into
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
