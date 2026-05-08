# Schema: Feints

[Back: Data Schemas](./README.md)

## Purpose

Feints are exchange-only attack replacements/modifiers. A feint is always chosen
together with an attack target and is resolved through the normal exchange
pipeline: accuracy, dodge, parry, block, hit, crit, damage, effects, and logs.

Feints are not standalone instant actions. Standalone buffs, debuffs, direct
damage, healing, and item-like actions belong to abilities, effects, gifts, or
items.

## Ownership

Feints are split into three layers:

```text
technical
  Runtime math and pipeline behavior.

descriptive
  UI text, icon, library text, and combat log templates.

availability
  Rules that decide which actor receives a feint in known_feints / arsenal.
```

The same `feint_id` can be granted by weapon mastery, stance, item, monster kit,
or another future source. The feint definition itself is written once.

## Runtime Flow

```text
catalog feint
  -> availability builder adds feint_id to combat.loadout.known_feints
  -> combat lifecycle copies known_feints to meta.feints.arsenal
  -> FeintService deals affordable feints from arsenal into meta.feints.hand
  -> combat dashboard sends feint_id and pinned state only
  -> client hydrates icon/text from catalog by combat.feint.<feint_id>
  -> player selects feint_id with an exchange attack
  -> pipeline applies feint technical config before resolver
  -> resolver produces normal attack outcome
  -> log service formats descriptive event text from catalog and resolver result
```

## Technical Contract

```python
class FeintTechnicalDTO(BaseModel):
    feint_id: str

    cost: FeintCostDTO
    target: TargetType = TargetType.SINGLE_ENEMY
    target_count: int = 1

    raw_mutations: dict[str, str] | None = None
    pipeline_mutations: dict[str, Any] | None = None
    triggers: list[str] | None = None
    override_damage: tuple[float, float] | None = None
    effects: list[dict[str, Any]] | None = None
```

Rules:

- `feint_id` is the stable runtime key, for example `sand_throw`.
- `cost.tactics` uses tactical token names: `hit`, `crit`, `block`, `parry`,
  `dodge`, `tempo`.
- Cost is catalog/runtime data. The frontend should hydrate display cost from
  the catalog by `feint_id`; combat state should not duplicate static cost
  unless a future mechanic creates actor-specific dynamic cost.
- Runtime may reserve token cost inside `meta.feints.hand` while cards are
  visible. UI actor tokens must be restored at the backend view boundary:
  `visible_tokens = meta.tokens + sum(meta.feints.hand costs)`. The player sees
  the total available token pool and perceives payment as happening on click.
- `raw_mutations` and `pipeline_mutations` are applied before resolver math.
- `triggers` attach existing trigger rules to the exchange.
- `effects` are consequences, normally applied after a valid hit.
- A feint must be valid only for exchange attacks.

## Descriptive Contract

Each feint has `CombatDescriptionDTO` with taxonomy variants. For now the
default authoring target is `humanoid`; beast/monster-family variants can be
expanded later.

```python
class CombatTaxonomyDescriptionDTO(BaseModel):
    icon: str
    display_name: str
    ui_label: str
    short_description: str
    long_description: str
    tooltip: str
    event_texts: CombatEventTextSetDTO
```

Field meaning:

```text
icon
  SVG/icon path or asset key shown near the feint label.

display_name
  Short library/catalog name: "Бросок песка", "Подсечка древком".

ui_label
  Button text: "Поймать момент и бросить песок в глаза".

short_description
  Compact UI description under or near the button.

long_description
  Hover/details/library explanation.

tooltip
  Optional short microcopy. If it duplicates long_description, prefer
  long_description for hover/details.

event_texts
  Combat log templates. These are separate from UI text.
```

## Combat Log Contract

Feint logs are descriptive templates, not hardcoded result strings. Combat state
does not carry these strings. A dedicated log service resolves `catalog_key`,
selects taxonomy, combines resolver output, and formats `event_texts`.

`event_texts.use` may be used as the opening part of the exchange sentence.
Outcome templates complete it:

```python
event_texts=CombatEventTextSetDTO(
    use=[
        "{source} опускает древко и ищет ноги {target}",
    ],
    hit=[
        "и цепляет его ноги древком, нанося {damage} урона.",
    ],
    miss=[
        "но {target} переступает через древко и сохраняет равновесие.",
    ],
    parry=[
        "но {target} сбивает древко в сторону.",
    ],
    block=[
        "но {target} принимает движение на щит.",
    ],
    dodge=[
        "но {target} отскакивает раньше, чем древко достает до ног.",
    ],
)
```

The log builder may format:

```text
{use}, {outcome}
```

Available template values should include at least:

```text
source, target, feint, damage, healing, effect, resource, outcome
```

## Taxonomy

Current descriptive variants:

```text
humanoid
beast
```

Default writing target is `humanoid`. Beast texts should be used when the target
or source taxonomy is beast/monster-like. Later this can expand to monster
families or races.

## Definition Files

Definition files group feints by their meaning, not by who grants them:

```text
feints/definitions/
  regular.py       # basic combat feints available from common combat training
  dirty.py         # sand, low blows, blinding, cheap tricks
  weapon_moves.py  # movements tied to weapon classes
```

The current code still has `tactical.py` for basic combat feints; it should be
treated as the legacy/current name for the future `regular.py` split.

Availability rules should live separately:

```text
feints/availability.py
```

Example:

```python
COMMON_FEINTS = [
    "true_strike",
    "defensive_strike",
]

WEAPON_MASTERY_FEINTS = {
    "skill_polearms": [
        {"feint_id": "polearm_trip", "min_skill": 0.25},
    ],
}

STANCE_FEINTS = {
    "stance_dirty": [
        {"feint_id": "sand_throw", "min_skill": 0.0},
    ],
}
```

## Example: Dirty Feint

```python
FeintCatalogEntryDTO(
    key="combat.feint.sand_throw",
    technical=FeintTechnicalDTO(
        feint_id="sand_throw",
        cost=FeintCostDTO(tactics={"tempo": 3}),
        target=TargetType.SINGLE_ENEMY,
        raw_mutations={"physical_damage_mult": "-0.8"},
        effects=[{"id": "blind", "params": {"duration": 2}}],
    ),
    descriptive=build_combat_description(
        resource_type="feints",
        resource_id="sand_throw",
        icon="combat/feints/sand_throw.svg",
        display_name="Бросок песка",
        ui_label="Поймать момент и бросить песок в глаза",
        short_description="Мешает цели защищаться.",
        humanoid_long_description=(
            "Грязный прием: исполнитель ловит короткую паузу в размене и "
            "бросает песок в лицо цели, чтобы сорвать защитную реакцию."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} ловит момент и бросает песок в глаза {target}"],
            hit=["и попадает, заставляя {target} сбиться с защиты."],
            miss=["но {target} отворачивается, и песок летит мимо."],
            dodge=["но {target} уходит от грязного приема."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} бросает горсть песка в морду {target}"],
            hit=["и песок попадает в глаза {target}."],
            miss=["но {target} мотает головой и избегает приема."],
        ),
    ),
)
```

## Example: Weapon Feint

```python
FeintCatalogEntryDTO(
    key="combat.feint.polearm_trip",
    technical=FeintTechnicalDTO(
        feint_id="polearm_trip",
        cost=FeintCostDTO(tactics={"tempo": 1, "dodge": 1}),
        target=TargetType.SINGLE_ENEMY,
        triggers=["control.stagger_on_hit"],
    ),
    descriptive=build_combat_description(
        resource_type="feints",
        resource_id="polearm_trip",
        icon="combat/feints/polearm_trip.svg",
        display_name="Подсечка древком",
        ui_label="Зацепить ноги древком и сбить темп",
        short_description="Может нарушить устойчивость цели.",
        humanoid_long_description=(
            "Движение для копий, посохов и древкового оружия: исполнитель "
            "цепляет ноги или опору цели, мешая ей уклоняться."
        ),
        humanoid_event_texts=CombatEventTextSetDTO(
            use=["{source} опускает древко и ищет ноги {target}"],
            hit=["и цепляет его ноги древком."],
            miss=["но {target} переступает через древко и сохраняет равновесие."],
            parry=["но {target} сбивает древко в сторону."],
            block=["но {target} принимает движение на щит."],
            dodge=["но {target} отскакивает раньше, чем древко достает до ног."],
        ),
        beast_event_texts=CombatEventTextSetDTO(
            use=["{source} ведет древко низко, ловя рывок {target}"],
            hit=["и сбивает шаг {target} ударом древка."],
            miss=["но {target} перескакивает через древко."],
        ),
    ),
)
```
