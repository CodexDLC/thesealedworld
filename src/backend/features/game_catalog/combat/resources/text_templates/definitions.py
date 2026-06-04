from __future__ import annotations

from src.backend.features.game_catalog.combat.resources.abilities import get_all_ability_catalog_entries
from src.backend.features.game_catalog.combat.resources.basic_exchanges import get_all_basic_exchange_entries
from src.backend.features.game_catalog.combat.resources.effects import get_all_effect_catalog_entries
from src.backend.features.game_catalog.combat.resources.effects.schemas import EffectType
from src.backend.features.game_catalog.combat.resources.feints import get_all_feint_catalog_entries
from src.backend.features.game_catalog.combat.resources.items import get_all_combat_item_action_catalog_entries
from src.backend.features.game_catalog.combat.resources.text_templates.schemas import CombatTextTemplateRecipeDTO

TARGET_BODIES = ("humanoid", "beast")

TRUE_STRIKE_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = ()

BASIC_EXCHANGE_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = ()


GENERIC_BASIC_EXCHANGE_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = ()


_WEAPON_FORM_BY_SKILL: dict[str, dict[str, str]] = {
    "skill_swords": {
        "hit": "body.humanoid.weapon_form.skill_swords.cutting_line",
        "crit": "body.humanoid.weapon_form.skill_swords.guard_cut",
        "avoidance": "body.humanoid.weapon_form.skill_swords.short_cut",
    },
    "skill_fencing": {
        "hit": "body.humanoid.weapon_form.skill_fencing.thrust",
        "crit": "body.humanoid.weapon_form.skill_fencing.point_line",
        "avoidance": "body.humanoid.weapon_form.skill_fencing.low_cut",
    },
    "skill_polearms": {
        "hit": "body.humanoid.weapon_form.skill_polearms.thrust",
        "crit": "body.humanoid.weapon_form.skill_polearms.long_reach",
        "avoidance": "body.humanoid.weapon_form.skill_polearms.sweep",
    },
    "skill_macing": {
        "hit": "body.humanoid.weapon_form.skill_macing.crushing_arc",
        "crit": "body.humanoid.weapon_form.skill_macing.break_line",
        "avoidance": "body.humanoid.weapon_form.skill_macing.short_bash",
    },
    "skill_archery": {
        "hit": "body.humanoid.weapon_form.skill_archery.moving_shot",
        "crit": "body.humanoid.weapon_form.skill_archery.aimed_shot",
        "avoidance": "body.humanoid.weapon_form.skill_archery.quick_shot",
    },
    "skill_unarmed": {
        "hit": "body.humanoid.weapon_form.skill_unarmed.straight",
        "crit": "body.humanoid.weapon_form.skill_unarmed.elbow",
        "avoidance": "body.humanoid.weapon_form.skill_unarmed.grapple",
    },
    "skill_shield_mastery": {
        "hit": "body.humanoid.weapon_form.skill_shield_mastery.shield_bash",
        "crit": "body.humanoid.weapon_form.skill_shield_mastery.shield_press",
        "avoidance": "body.humanoid.weapon_form.skill_shield_mastery.shield_bash",
    },
    "skill_dual_wield": {
        "hit": "body.humanoid.weapon_form.skill_dual_wield.second_line",
        "crit": "body.humanoid.weapon_form.skill_dual_wield.cross_pressure",
        "avoidance": "body.humanoid.weapon_form.skill_dual_wield.second_line",
    },
}


def _basic_exchange_delivery(skill_key: str) -> str:
    if skill_key == "natural_weapon":
        return "natural"
    return "unarmed" if skill_key == "skill_unarmed" else "weapon"


def _is_natural_basic_exchange(skill_key: str) -> bool:
    return skill_key == "natural_weapon"


def _natural_weapon_phrase_key(weapon_class: str, hand: str = "main") -> str:
    if hand == "off":
        return {
            "fangs": "body.beast.natural_weapon.offhand.fangs",
            "claws": "body.beast.natural_weapon.offhand.claws",
            "default": "body.beast.natural_weapon.offhand.default",
        }.get(weapon_class, "body.beast.natural_weapon.offhand.default")
    return {
        "fangs": "body.beast.natural_weapon.default.fangs",
        "claws": "body.beast.natural_weapon.default.claws",
        "default": "body.beast.natural_weapon.default.teeth",
    }.get(weapon_class, "body.beast.natural_weapon.default.teeth")


def _natural_approach_phrase_key(weapon_class: str, hand: str = "main") -> str:
    if hand == "off":
        return "body.beast.approach.offhand.default"
    return {
        "fangs": "body.beast.approach.medium.low_lunge",
        "claws": "body.beast.approach.small.dart",
        "default": "body.beast.approach.default.circle",
    }.get(weapon_class, "body.beast.approach.default.circle")


def _natural_contact_phrase_key(weapon_class: str, outcome: str, target_body: str) -> str:
    if target_body == "beast":
        if weapon_class == "fangs":
            return (
                "body.beast.contact_vs_beast.default.neck"
                if outcome == "crit"
                else "body.beast.contact_vs_beast.default.scruff"
            )
        if weapon_class == "claws":
            return "body.beast.contact_vs_beast.default.flank"
        return "body.beast.contact_vs_beast.default.leg"
    if weapon_class == "fangs":
        return (
            "body.beast.contact_vs_humanoid.default.throat"
            if outcome == "crit"
            else "body.beast.contact_vs_humanoid.default.leg"
        )
    if weapon_class == "claws":
        return (
            "body.beast.contact_vs_humanoid.default.arm"
            if outcome == "crit"
            else "body.beast.contact_vs_humanoid.default.open_side"
        )
    return "body.beast.contact_vs_humanoid.default.below_guard"


def _natural_impact_phrase_key(weapon_class: str, outcome: str, target_body: str) -> str:
    if target_body == "beast":
        if weapon_class == "fangs":
            return (
                "body.beast.impact_vs_beast.default.neck"
                if outcome == "crit"
                else "body.beast.impact_vs_beast.default.scruff"
            )
        if weapon_class == "claws":
            return "body.beast.impact_vs_beast.default.flank"
        return "body.beast.impact_vs_beast.default.leg"
    if weapon_class == "fangs":
        return (
            "body.beast.impact_vs_humanoid.default.throat"
            if outcome == "crit"
            else "body.beast.impact_vs_humanoid.medium.fangs"
        )
    if weapon_class == "claws":
        return (
            "body.beast.impact_vs_humanoid.default.arm"
            if outcome == "crit"
            else "body.beast.impact_vs_humanoid.default.claws"
        )
    return "body.beast.impact_vs_humanoid.default.leg"


def _natural_reaction_phrase_key(outcome: str, target_body: str) -> str:
    if target_body == "beast":
        return {
            "miss": "body.beast.reaction.miss.natural",
            "dodge": "body.beast.reaction.dodge.side_leap",
            "parry": "body.beast.reaction.parry.paw_swipe",
            "block": "body.beast.reaction.block.shoulder",
        }[outcome]
    return {
        "miss": "body.humanoid.reaction.miss.natural",
        "dodge": "body.humanoid.reaction.dodge.sidestep",
        "parry": "body.humanoid.reaction.parry.deflect",
        "block": "body.humanoid.reaction.block.shield_take",
    }[outcome]


def _natural_basic_exchange_phrase_keys(
    weapon_class: str,
    outcome: str,
    target_body: str,
    hand: str = "main",
) -> dict[str, str]:
    keys = {
        "approach": _natural_approach_phrase_key(weapon_class, hand),
        "natural_weapon": _natural_weapon_phrase_key(weapon_class, hand),
    }
    if outcome in {"hit", "crit"}:
        keys.update(
            {
                "contact": _natural_contact_phrase_key(weapon_class, outcome, target_body),
                "impact": _natural_impact_phrase_key(weapon_class, outcome, target_body),
                "result": "common.result.damage.hp",
            }
        )
    elif outcome == "miss":
        keys["reaction"] = _natural_reaction_phrase_key(outcome, target_body)
    else:
        keys.update(
            {
                "contact": _natural_contact_phrase_key(weapon_class, outcome, target_body),
                "reaction": _natural_reaction_phrase_key(outcome, target_body),
            }
        )
    return keys


def _basic_exchange_weapon_form(skill_key: str, outcome: str) -> str:
    forms = _WEAPON_FORM_BY_SKILL.get(skill_key) or _WEAPON_FORM_BY_SKILL["skill_swords"]
    form_type = "crit" if outcome == "crit" else "hit" if outcome == "hit" else "avoidance"
    return forms[form_type]


def _basic_exchange_approach(skill_key: str) -> str:
    if skill_key == "skill_archery":
        return "body.humanoid.approach.ranged.draw"
    if skill_key == "skill_unarmed":
        return "body.humanoid.approach.unarmed.low"
    return "body.humanoid.approach.weapon.measured"


def _basic_exchange_contact(skill_key: str, outcome: str, target_body: str) -> str:
    if target_body == "beast":
        if skill_key == "skill_archery":
            return (
                "body.humanoid.contact_vs_beast.ranged.weak_spot"
                if outcome == "crit"
                else "body.humanoid.contact_vs_beast.ranged.center_mass"
            )
        if skill_key == "skill_unarmed":
            return "body.humanoid.contact_vs_beast.unarmed.snout"
        return "body.humanoid.contact_vs_beast.default.flank"
    if skill_key == "skill_archery":
        return (
            "body.humanoid.contact_vs_humanoid.ranged.weak_spot"
            if outcome == "crit"
            else "body.humanoid.contact_vs_humanoid.ranged.center_mass"
        )
    if skill_key == "skill_macing":
        return "body.humanoid.contact_vs_humanoid.default.break_guard"
    if skill_key == "skill_unarmed":
        return "body.humanoid.contact_vs_humanoid.default.body_blow"
    return "body.humanoid.contact_vs_humanoid.default.open_side"


def _basic_exchange_impact(skill_key: str, outcome: str, target_body: str) -> str:
    if target_body == "beast":
        if skill_key == "skill_archery":
            return (
                "body.humanoid.impact_vs_beast.ranged.crit.arrow"
                if outcome == "crit"
                else "body.humanoid.impact_vs_beast.ranged.hit.arrow"
            )
        return (
            "body.humanoid.impact_vs_beast.crit.stagger"
            if outcome == "crit"
            else "body.humanoid.impact_vs_beast.hit.flank"
        )
    if skill_key == "skill_archery":
        return (
            "body.humanoid.impact_vs_humanoid.ranged.crit.arrow"
            if outcome == "crit"
            else "body.humanoid.impact_vs_humanoid.ranged.hit.arrow"
        )
    return (
        "body.humanoid.impact_vs_humanoid.crit.break"
        if outcome == "crit"
        else "body.humanoid.impact_vs_humanoid.hit.side"
    )


def _basic_exchange_reaction(outcome: str, target_body: str) -> str:
    if target_body == "beast":
        return {
            "miss": "body.beast.reaction.miss.pass",
            "dodge": "body.beast.reaction.dodge.side_leap",
            "parry": "body.beast.reaction.parry.paw_swipe",
            "block": "body.beast.reaction.block.shoulder",
        }[outcome]
    return {
        "miss": "body.humanoid.reaction.miss.void",
        "dodge": "body.humanoid.reaction.dodge.sidestep",
        "parry": "body.humanoid.reaction.parry.deflect",
        "block": "body.humanoid.reaction.block.shield_take",
    }[outcome]


def _basic_exchange_phrase_keys(skill_key: str, outcome: str, target_body: str) -> dict[str, str]:
    keys = {
        "approach": _basic_exchange_approach(skill_key),
        "weapon_form": _basic_exchange_weapon_form(skill_key, outcome),
    }
    if outcome in {"hit", "crit"}:
        keys.update(
            {
                "contact": _basic_exchange_contact(skill_key, outcome, target_body),
                "impact": _basic_exchange_impact(skill_key, outcome, target_body),
                "result": "common.result.damage.hp",
            }
        )
    elif outcome == "miss":
        keys["reaction"] = _basic_exchange_reaction(outcome, target_body)
    else:
        keys.update(
            {
                "contact": _basic_exchange_contact(skill_key, outcome, target_body),
                "reaction": _basic_exchange_reaction(outcome, target_body),
            }
        )
    return keys


def _build_basic_exchange_template_recipes() -> tuple[CombatTextTemplateRecipeDTO, ...]:
    recipes: list[CombatTextTemplateRecipeDTO] = []
    for entry in get_all_basic_exchange_entries():
        exchange_id = entry.technical.exchange_id
        skill_key = entry.technical.skill_key
        source_body = "beast" if _is_natural_basic_exchange(skill_key) else "humanoid"
        delivery = _basic_exchange_delivery(skill_key)
        base_tags = ["exchange", delivery, skill_key, entry.technical.source_type]
        for target_body in TARGET_BODIES:
            body_pair = f"{source_body}_to_{target_body}"
            for outcome in ("hit", "crit", "miss", "dodge", "parry", "block"):
                if _is_natural_basic_exchange(skill_key):
                    phrase_keys = _natural_basic_exchange_phrase_keys(
                        entry.technical.weapon_class,
                        outcome,
                        target_body,
                        entry.technical.hand,
                    )
                    is_bite = (entry.technical.weapon_class == "fangs") or (
                        entry.technical.weapon_class == "default" and entry.technical.hand != "off"
                    )
                    verb = ("кусает" if outcome in {"hit", "crit"} else "пытается укусить") if is_bite else "бьёт"
                    pattern = (
                        f"{{approach}}, {verb} {{natural_weapon}} и {{contact}}; {{impact}}, {{result}}."
                        if outcome in {"hit", "crit"}
                        else f"{{approach}}, {verb} {{natural_weapon}}; но {{reaction}}."
                        if outcome == "miss"
                        else f"{{approach}}, {verb} {{natural_weapon}} и {{contact}}; но {{reaction}}."
                    )
                else:
                    phrase_keys = _basic_exchange_phrase_keys(skill_key, outcome, target_body)
                    pattern = (
                        "{approach}, {weapon_form} и {contact}; {impact}, {result}."
                        if outcome in {"hit", "crit"}
                        else "{approach}, {weapon_form}; но {reaction}."
                        if outcome == "miss"
                        else "{approach}, {weapon_form} и {contact}; но {reaction}."
                    )
                recipes.append(
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.exchange.{exchange_id}.{outcome}.{body_pair}.{delivery}",
                        resource_type="basic_exchange",
                        resource_id=exchange_id,
                        catalog_key=entry.key,
                        outcome=outcome,
                        body_pair=body_pair,
                        delivery=delivery,
                        pattern=pattern,
                        phrase_keys=phrase_keys,
                        tags=[*base_tags, outcome, target_body],
                    )
                )
    return tuple(recipes)


BASIC_WEAPON_MASTERY_TEMPLATE_RECIPES = _build_basic_exchange_template_recipes()


DEFAULT_BASIC_EXCHANGE_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.default.hit",
        resource_type="basic_exchange",
        resource_id="default",
        catalog_key="combat.exchange.default",
        outcome="hit",
        pattern="{source} атакует {target}, нанося {damage} урона. (F)",
        tags=["exchange", "default", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.default.crit",
        resource_type="basic_exchange",
        resource_id="default",
        catalog_key="combat.exchange.default",
        outcome="crit",
        pattern="{source} атакует {target}, нанося {damage} урона. (F)",
        tags=["exchange", "default", "fallback", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.default.miss",
        resource_type="basic_exchange",
        resource_id="default",
        catalog_key="combat.exchange.default",
        outcome="miss",
        pattern="{source} атакует {target}, но промахивается. (F)",
        tags=["exchange", "default", "fallback", "miss"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.default.dodge",
        resource_type="basic_exchange",
        resource_id="default",
        catalog_key="combat.exchange.default",
        outcome="dodge",
        pattern="{source} атакует {target}, но цель уходит от атаки. (F)",
        tags=["exchange", "default", "fallback", "dodge"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.default.parry",
        resource_type="basic_exchange",
        resource_id="default",
        catalog_key="combat.exchange.default",
        outcome="parry",
        pattern="{source} атакует {target}, но атака парирована. (F)",
        tags=["exchange", "default", "fallback", "parry"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.default.block",
        resource_type="basic_exchange",
        resource_id="default",
        catalog_key="combat.exchange.default",
        outcome="block",
        pattern="{source} атакует {target}, но защита гасит удар. (F)",
        tags=["exchange", "default", "fallback", "block"],
    ),
)


DEFAULT_FEINT_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = ()


def _feint_descriptive_exchange_pattern(entry, outcome: str) -> str | None:
    variant = entry.descriptive.variants.get("humanoid")
    if variant is None:
        return None
    return variant.event_texts.exchange_template(outcome)


def _feint_weapon_phrase_keys(entry, outcome: str, impact_key: str) -> dict[str, str]:
    tags = set(entry.technical.applicability_tags or ())
    if {"skill_archery", "skill_ranged_combat"} & tags:
        return {
            "approach": "body.humanoid.approach.ranged.draw",
            "weapon_form": (
                "body.humanoid.weapon_form.skill_archery.aimed_shot"
                if outcome == "crit"
                else "body.humanoid.weapon_form.skill_archery.moving_shot"
            ),
            "contact": (
                "body.humanoid.contact_vs_humanoid.ranged.weak_spot"
                if outcome == "crit"
                else "body.humanoid.contact_vs_humanoid.ranged.center_mass"
            ),
            "impact": (
                "body.humanoid.impact_vs_humanoid.ranged.crit.arrow"
                if outcome == "crit"
                else "body.humanoid.impact_vs_humanoid.ranged.hit.arrow"
            ),
            "result": "common.result.damage.hp",
        }
    return {
        "approach": "body.humanoid.approach.weapon.measured",
        "weapon_form": "body.humanoid.weapon_form.skill_swords.cutting_line",
        "contact": "body.humanoid.contact_vs_humanoid.default.open_side",
        "impact": impact_key,
        "result": "common.result.damage.hp",
    }


def _build_generic_feint_template_recipes() -> tuple[CombatTextTemplateRecipeDTO, ...]:
    existing = {recipe.template_key for recipe in TRUE_STRIKE_TEMPLATE_RECIPES}
    recipes: list[CombatTextTemplateRecipeDTO] = []
    for entry in get_all_feint_catalog_entries():
        feint_id = entry.technical.feint_id
        for outcome, impact_key, tags in (
            ("hit", "body.humanoid.impact_vs_humanoid.hit.side", ["feint", "weapon"]),
            ("crit", "body.humanoid.impact_vs_humanoid.crit.break", ["feint", "weapon", "crit"]),
        ):
            key = f"combat.feint.{feint_id}.{outcome}.humanoid_to_humanoid.weapon"
            if key in existing:
                continue
            pattern = "{approach}, {weapon_form} и {contact}; {impact}, {result}."
            recipes.append(
                CombatTextTemplateRecipeDTO(
                    template_key=key,
                    resource_type="feint",
                    resource_id=feint_id,
                    catalog_key=entry.key,
                    outcome=outcome,
                    body_pair="humanoid_to_humanoid",
                    delivery="weapon",
                    pattern=pattern,
                    phrase_keys=_feint_weapon_phrase_keys(entry, outcome, impact_key),
                    tags=tags,
                )
            )
        for outcome, tags in (
            ("miss", ["feint", "weapon", "avoidance", "miss"]),
            ("dodge", ["feint", "weapon", "avoidance", "dodge"]),
            ("parry", ["feint", "weapon", "avoidance", "parry"]),
            ("block", ["feint", "weapon", "avoidance", "block"]),
        ):
            key = f"combat.feint.{feint_id}.{outcome}.humanoid_to_humanoid.weapon"
            if key in existing:
                continue
            pattern = _feint_descriptive_exchange_pattern(entry, outcome)
            if not pattern:
                continue
            recipes.append(
                CombatTextTemplateRecipeDTO(
                    template_key=key,
                    resource_type="feint",
                    resource_id=feint_id,
                    catalog_key=entry.key,
                    outcome=outcome,
                    body_pair="humanoid_to_humanoid",
                    delivery="weapon",
                    pattern=pattern,
                    tags=tags,
                )
            )
    return tuple(recipes)


GENERIC_FEINT_TEMPLATE_RECIPES = _build_generic_feint_template_recipes()


def _effect_patterns(effect_type: EffectType) -> dict[str, str]:
    if effect_type == EffectType.DOT:
        return {
            "apply": "{target} получает {effect}.",
            "tick": "{effect} терзает {target}: -{value} {resource}.",
            "expire": "{effect} на {target} заканчивается.",
            "cleanse": "{effect} на {target} снят.",
            "resist": "{target} сопротивляется: {effect} не закрепляется.",
        }
    if effect_type == EffectType.HOT:
        return {
            "apply": "{target} получает {effect}.",
            "tick": "{effect} действует: {target} восстанавливает {value} {resource}.",
            "expire": "{effect} на {target} заканчивается.",
            "cleanse": "{effect} на {target} прерван.",
            "resist": "{target} не принимает {effect}.",
        }
    if effect_type == EffectType.CONTROL:
        return {
            "apply": "{target} попадает под {effect}.",
            "tick": "{effect} удерживает {target}.",
            "expire": "{target} выходит из {effect}.",
            "cleanse": "{effect} на {target} снят.",
            "resist": "{target} сопротивляется {effect}.",
        }
    return {
        "apply": "{target} получает {effect}.",
        "tick": "{effect} действует на {target}.",
        "expire": "{effect} на {target} заканчивается.",
        "cleanse": "{effect} на {target} снят.",
        "resist": "{target} сопротивляется {effect}.",
    }


def _build_effect_template_recipes() -> tuple[CombatTextTemplateRecipeDTO, ...]:
    recipes: list[CombatTextTemplateRecipeDTO] = []
    for entry in get_all_effect_catalog_entries():
        effect_id = entry.technical.effect_id
        patterns = _effect_patterns(entry.technical.type)
        tick_resources = tuple(sorted(entry.technical.resource_impact)) or ("state",)
        for target_body in TARGET_BODIES:
            for action in ("apply", "expire", "cleanse", "resist"):
                recipes.append(
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.effect.{effect_id}.{action}.{target_body}",
                        resource_type="effect",
                        resource_id=effect_id,
                        catalog_key=entry.key,
                        outcome=action,
                        target_body=target_body,
                        pattern=patterns[action],
                        tags=["effect", str(entry.technical.type), action, *entry.technical.tags],
                    )
                )
            for resource in tick_resources:
                recipes.append(
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.effect.{effect_id}.tick.{target_body}.{resource}",
                        resource_type="effect",
                        resource_id=effect_id,
                        catalog_key=entry.key,
                        outcome="tick",
                        target_body=target_body,
                        delivery=resource,
                        pattern=patterns["tick"],
                        tags=["effect", str(entry.technical.type), "tick", resource, *entry.technical.tags],
                    )
                )
    return tuple(recipes)


EFFECT_TEMPLATE_RECIPES = _build_effect_template_recipes()


def _ability_event_pattern(entry, event: str, target_body: str = "humanoid") -> str | None:
    resolved = entry.descriptive.resolve_event_template(event, [target_body])
    return resolved.text if resolved else None


def _ability_outcome_pattern(
    entry,
    *,
    outcome: str,
    target_body: str = "humanoid",
    fallback: str,
) -> str:
    event = {
        "cast": "use",
        "apply": "apply_effect",
    }.get(outcome, outcome)
    return _ability_event_pattern(entry, event, target_body) or fallback


def _build_ability_template_recipes() -> tuple[CombatTextTemplateRecipeDTO, ...]:
    recipes: list[CombatTextTemplateRecipeDTO] = []
    for entry in get_all_ability_catalog_entries():
        ability_id = entry.technical.ability_id
        recipes.extend(
            [
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.ability.{ability_id}.cast.single",
                    resource_type="ability",
                    resource_id=ability_id,
                    catalog_key=entry.key,
                    outcome="cast",
                    delivery="single",
                    pattern=_ability_outcome_pattern(
                        entry,
                        outcome="cast",
                        fallback="{source} применяет {ability} на {target}: {target_results}.",
                    ),
                    tags=["ability", "cast", "single"],
                ),
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.ability.{ability_id}.cast.area",
                    resource_type="ability",
                    resource_id=ability_id,
                    catalog_key=entry.key,
                    outcome="area_result",
                    delivery="area",
                    pattern=_ability_outcome_pattern(
                        entry,
                        outcome="area_result",
                        fallback="{source} применяет {ability}: {target_results}.",
                    ),
                    tags=["ability", "cast", "area"],
                ),
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.ability.{ability_id}.no_resource",
                    resource_type="ability",
                    resource_id=ability_id,
                    catalog_key=entry.key,
                    outcome="no_resource",
                    pattern=_ability_outcome_pattern(
                        entry,
                        outcome="no_resource",
                        fallback="{source} пытается применить {ability}, но ресурса не хватает.",
                    ),
                    tags=["ability", "no_resource"],
                ),
            ]
        )
        for target_body in TARGET_BODIES:
            for outcome, fallback in (
                ("hit", "{target} получает {damage} урона"),
                ("crit", "{target} получает критический удар от {ability}"),
                ("heal", "{target} восстанавливает {healing} здоровья"),
                ("apply", "{target} получает {effect}"),
                ("miss", "{target} избегает {ability}"),
                ("dodge", "{target} уклоняется от {ability}"),
                ("parry", "{target} парирует {ability}"),
                ("block", "{target} блокирует {ability}"),
            ):
                recipes.append(
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.ability.{ability_id}.target.{outcome}.{target_body}",
                        resource_type="ability",
                        resource_id=ability_id,
                        catalog_key=entry.key,
                        outcome=outcome,
                        target_body=target_body,
                        pattern=_ability_outcome_pattern(
                            entry,
                            outcome=outcome,
                            target_body=target_body,
                            fallback=fallback,
                        ),
                        tags=["ability", "target", outcome, target_body],
                    )
                )
    return tuple(recipes)


ABILITY_TEMPLATE_RECIPES = _build_ability_template_recipes()


ABILITY_DEFAULT_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.cast.single",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="cast",
        delivery="single",
        pattern="{source} применяет {ability} на {target}. (F)",
        tags=["ability", "default", "fallback", "cast"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.cast.area",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="area_result",
        delivery="area",
        pattern="{source} применяет {ability}: {target_results}. (F)",
        tags=["ability", "default", "fallback", "area"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.no_resource",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="no_resource",
        pattern="{source} не может применить {ability}. (F)",
        tags=["ability", "default", "fallback", "no_resource"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.target.hit",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="hit",
        pattern="{target} получает {damage} урона от {ability}. (F)",
        tags=["ability", "default", "fallback", "hit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.target.heal",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="heal",
        pattern="{target} восстанавливает {healing} здоровья от {ability}. (F)",
        tags=["ability", "default", "fallback", "heal"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.target.apply",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="apply",
        pattern="{target} получает эффект от {ability}. (F)",
        tags=["ability", "default", "fallback", "apply"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.ability.default.target.miss",
        resource_type="ability",
        resource_id="default",
        catalog_key="combat.ability.default",
        outcome="miss",
        pattern="{target} избегает {ability}. (F)",
        tags=["ability", "default", "fallback", "miss"],
    ),
)


DEATH_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    # --- humanoid target ---
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.damage.humanoid",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="humanoid",
        pattern="{death}",
        phrase_keys={"death": "death.humanoid.damage.struck_down"},
        tags=["death", "damage", "humanoid"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.dot.humanoid",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="humanoid",
        pattern="{death}",
        phrase_keys={"death": "death.humanoid.dot.consumed_by"},
        tags=["death", "dot", "humanoid"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.ability.humanoid",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="humanoid",
        pattern="{death}",
        phrase_keys={"death": "death.humanoid.ability.finished_by"},
        tags=["death", "ability", "humanoid"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.execute.humanoid",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="humanoid",
        pattern="{death}",
        phrase_keys={"death": "death.humanoid.execute.judgement"},
        tags=["death", "execute", "humanoid"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.unknown.humanoid",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="humanoid",
        pattern="{death}",
        phrase_keys={"death": "death.common.unknown.collapses"},
        tags=["death", "unknown", "humanoid"],
    ),
    # --- beast target ---
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.damage.beast",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="beast",
        pattern="{death}",
        phrase_keys={"death": "death.beast.damage.brought_down"},
        tags=["death", "damage", "beast"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.dot.beast",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="beast",
        pattern="{death}",
        phrase_keys={"death": "death.beast.dot.poison_end"},
        tags=["death", "dot", "beast"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.ability.beast",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="beast",
        pattern="{death}",
        phrase_keys={"death": "death.beast.ability.felled"},
        tags=["death", "ability", "beast"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.execute.beast",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="beast",
        pattern="{death}",
        phrase_keys={"death": "death.beast.execute.put_down"},
        tags=["death", "execute", "beast"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.death.unknown.beast",
        resource_type="death",
        resource_id="death",
        catalog_key="combat.death",
        outcome="death",
        target_body="beast",
        pattern="{death}",
        phrase_keys={"death": "death.beast.unknown.falls_silent"},
        tags=["death", "unknown", "beast"],
    ),
)


# ---------------------------------------------------------------------------
# TRIGGER TEMPLATE RECIPES
# Specific per-trigger humanoid proc templates, lifted from humanoid_event_texts.
# Beast triggers fall through to the generic default key.
# ---------------------------------------------------------------------------
TRIGGER_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    # --- generic fallback (always present, covers any trigger without a specific key) ---
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.default.proc.humanoid",
        resource_type="trigger",
        resource_id="default",
        catalog_key="combat.trigger.default",
        outcome="proc",
        target_body="humanoid",
        pattern="{source} активирует {trigger}. (F)",
        tags=["trigger", "default", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.default.proc.beast",
        resource_type="trigger",
        resource_id="default",
        catalog_key="combat.trigger.default",
        outcome="proc",
        target_body="beast",
        pattern="{source} активирует {trigger}. (F)",
        tags=["trigger", "default", "beast", "fallback"],
    ),
    # --- weapon triggers ---
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.serrated_bleed_crit.crit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_serrated_bleed_crit",
        catalog_key="combat.trigger.weapon.serrated_bleed_crit",
        outcome="crit_proc",
        target_body="humanoid",
        pattern="{source} рассекает {target}; рана начинает кровоточить.",
        tags=["trigger", "weapon", "bleed", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.serrated_bleed_hit.hit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_serrated_bleed_hit",
        catalog_key="combat.trigger.weapon.serrated_bleed_hit",
        outcome="hit_proc",
        target_body="humanoid",
        pattern="{source} режет {target} коротким клинком.",
        tags=["trigger", "weapon", "bleed", "hit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.heavy_crit.crit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_heavy_crit",
        catalog_key="combat.trigger.weapon.heavy_crit",
        outcome="crit_proc",
        target_body="humanoid",
        pattern="{source} обрушивает тяжелый удар на {target}: {damage} урона.",
        tags=["trigger", "weapon", "heavy", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.impact_stun_crit.crit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_impact_stun_crit",
        catalog_key="combat.trigger.weapon.impact_stun_crit",
        outcome="crit_proc",
        target_body="humanoid",
        pattern="{source} сбивает {target} сокрушительным ударом.",
        tags=["trigger", "weapon", "stun", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.piercing_crit.crit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_piercing_crit",
        catalog_key="combat.trigger.weapon.piercing_crit",
        outcome="crit_proc",
        target_body="humanoid",
        pattern="{source} находит щель в защите {target}.",
        tags=["trigger", "weapon", "piercing", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.precision_crit.crit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_precision_crit",
        catalog_key="combat.trigger.weapon.precision_crit",
        outcome="crit_proc",
        target_body="humanoid",
        pattern="{source} ловит движение {target} точным критическим ударом.",
        tags=["trigger", "weapon", "precision", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.shieldbreaker_crit.crit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_shieldbreaker_crit",
        catalog_key="combat.trigger.weapon.shieldbreaker_crit",
        outcome="crit_proc",
        target_body="humanoid",
        pattern="{source} обводит защиту {target} цепным ударом.",
        tags=["trigger", "weapon", "shield", "crit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.knockdown_hit.hit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_knockdown_hit",
        catalog_key="combat.trigger.weapon.knockdown_hit",
        outcome="hit_proc",
        target_body="humanoid",
        pattern="{source} цепляет опору {target}.",
        tags=["trigger", "weapon", "knockdown", "hit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.evasive_shot.hit_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_evasive_shot",
        catalog_key="combat.trigger.weapon.evasive_shot",
        outcome="hit_proc",
        target_body="humanoid",
        pattern="{source} поражает {target} и смещается в выгодную позицию.",
        tags=["trigger", "weapon", "ranged", "hit"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.riposte_on_parry.parry_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_riposte_on_parry",
        catalog_key="combat.trigger.weapon.riposte_on_parry",
        outcome="parry_proc",
        target_body="humanoid",
        pattern="{target} парирует и сразу ищет ответную линию.",
        tags=["trigger", "weapon", "parry", "riposte"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.weapon.shield_bash_on_block.block_proc.humanoid",
        resource_type="trigger",
        resource_id="weapon_shield_bash_on_block",
        catalog_key="combat.trigger.weapon.shield_bash_on_block",
        outcome="block_proc",
        target_body="humanoid",
        pattern="{target} принимает удар щитом и отвечает корпусом.",
        tags=["trigger", "weapon", "shield", "block"],
    ),
    # --- style triggers ---
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.style.2h_ignore.proc.humanoid",
        resource_type="trigger",
        resource_id="style_2h_ignore",
        catalog_key="combat.trigger.style.2h_ignore",
        outcome="proc",
        target_body="humanoid",
        pattern="{source} пробивает защиту {target} мощным ударом.",
        tags=["trigger", "style", "proc"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.style.ranged_perfect_backstep.dodge_proc.humanoid",
        resource_type="trigger",
        resource_id="style_ranged_perfect_backstep",
        catalog_key="combat.trigger.style.ranged_perfect_backstep",
        outcome="dodge_proc",
        target_body="humanoid",
        pattern="{target} отрывается от {source} и закрепляет дальнюю позицию.",
        tags=["trigger", "style", "ranged_combat", "dodge"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.style.shield_reflect.block_proc.humanoid",
        resource_type="trigger",
        resource_id="style_shield_reflect",
        catalog_key="combat.trigger.style.shield_reflect",
        outcome="block_proc",
        target_body="humanoid",
        pattern="{target} частично гасит удар {source} щитом.",
        tags=["trigger", "style", "block"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.style.dual_cross_cut.proc.humanoid",
        resource_type="trigger",
        resource_id="style_dual_cross_cut",
        catalog_key="combat.trigger.style.dual_cross_cut",
        outcome="proc",
        target_body="humanoid",
        pattern="{source} усиливает критический удар перекрестным срезом.",
        tags=["trigger", "style", "dual_wield", "crit"],
    ),
    # --- dodge / accuracy triggers ---
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.dodge.counter_on_dodge.dodge_proc.humanoid",
        resource_type="trigger",
        resource_id="counter_on_dodge",
        catalog_key="combat.trigger.dodge.counter_on_dodge",
        outcome="dodge_proc",
        target_body="humanoid",
        pattern="{target} уклоняется от {source} и переходит в контратаку.",
        tags=["trigger", "dodge", "counter"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.accuracy.true_strike.proc.humanoid",
        resource_type="trigger",
        resource_id="true_strike",
        catalog_key="combat.trigger.accuracy.true_strike",
        outcome="proc",
        target_body="humanoid",
        pattern="{source} наносит неотвратимый удар по {target}.",
        tags=["trigger", "accuracy", "proc"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.trigger.miss.rage_on_miss.miss_proc.humanoid",
        resource_type="trigger",
        resource_id="rage_on_miss",
        catalog_key="combat.trigger.miss.rage_on_miss",
        outcome="miss_proc",
        target_body="humanoid",
        pattern="{source} промахивается, но ярость нарастает.",
        tags=["trigger", "miss", "rage"],
    ),
)


# ---------------------------------------------------------------------------
# GIFT TEMPLATE RECIPES
# Generic defaults only — gift_id is not available in combat action payload yet.
# Specific gift templates will be added when gift abilities carry their gift_id.
# ---------------------------------------------------------------------------
GIFT_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.cast.single",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="cast",
        delivery="single",
        pattern="{source} применяет {gift} на {target}. (F)",
        tags=["gift", "default", "cast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.cast.area",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="cast",
        delivery="area",
        pattern="{source} раскрывает {gift}. (F)",
        tags=["gift", "default", "area", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.no_resource",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="no_resource",
        pattern="{source} не может применить {gift}. (F)",
        tags=["gift", "default", "no_resource", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.hit.humanoid",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="hit",
        target_body="humanoid",
        pattern="{target} получает удар от {gift}. (F)",
        tags=["gift", "default", "hit", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.hit.beast",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="hit",
        target_body="beast",
        pattern="{target} получает удар от {gift}. (F)",
        tags=["gift", "default", "hit", "beast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.apply.humanoid",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="apply",
        target_body="humanoid",
        pattern="{target} получает эффект от {gift}. (F)",
        tags=["gift", "default", "apply", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.apply.beast",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="apply",
        target_body="beast",
        pattern="{target} получает эффект от {gift}. (F)",
        tags=["gift", "default", "apply", "beast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.heal.humanoid",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="heal",
        target_body="humanoid",
        pattern="{gift} восстанавливает {target}. (F)",
        tags=["gift", "default", "heal", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.heal.beast",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="heal",
        target_body="beast",
        pattern="{gift} восстанавливает {target}. (F)",
        tags=["gift", "default", "heal", "beast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.miss.humanoid",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="miss",
        target_body="humanoid",
        pattern="{target} избегает {gift}. (F)",
        tags=["gift", "default", "miss", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.gift.default.target.miss.beast",
        resource_type="gift",
        resource_id="default",
        catalog_key="combat.gift.default",
        outcome="miss",
        target_body="beast",
        pattern="{target} избегает {gift}. (F)",
        tags=["gift", "default", "miss", "beast", "fallback"],
    ),
)


# ---------------------------------------------------------------------------
# ITEM TEMPLATE RECIPES
# Generic defaults for item actions (fire_grenade, minor_healing_potion, etc.).
# Specific per-item templates can be added when items are active in combat.
# ---------------------------------------------------------------------------
ITEM_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.cast.single",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="cast",
        delivery="single",
        pattern="{source} использует {item} на {target}. (F)",
        tags=["item", "default", "cast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.cast.area",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="cast",
        delivery="area",
        pattern="{source} использует {item}. (F)",
        tags=["item", "default", "area", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.no_resource",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="no_resource",
        pattern="{source} не может использовать {item}. (F)",
        tags=["item", "default", "no_resource", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.hit.humanoid",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="hit",
        target_body="humanoid",
        pattern="{target} получает удар от {item}. (F)",
        tags=["item", "default", "hit", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.hit.beast",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="hit",
        target_body="beast",
        pattern="{target} получает удар от {item}. (F)",
        tags=["item", "default", "hit", "beast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.apply.humanoid",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="apply",
        target_body="humanoid",
        pattern="{target} получает эффект от {item}. (F)",
        tags=["item", "default", "apply", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.apply.beast",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="apply",
        target_body="beast",
        pattern="{target} получает эффект от {item}. (F)",
        tags=["item", "default", "apply", "beast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.heal.humanoid",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="heal",
        target_body="humanoid",
        pattern="{item} восстанавливает {target}. (F)",
        tags=["item", "default", "heal", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.heal.beast",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="heal",
        target_body="beast",
        pattern="{item} восстанавливает {target}. (F)",
        tags=["item", "default", "heal", "beast", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.miss.humanoid",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="miss",
        target_body="humanoid",
        pattern="{target} избегает {item}. (F)",
        tags=["item", "default", "miss", "humanoid", "fallback"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.item.default.target.miss.beast",
        resource_type="item",
        resource_id="default",
        catalog_key="combat.item.default",
        outcome="miss",
        target_body="beast",
        pattern="{target} избегает {item}. (F)",
        tags=["item", "default", "miss", "beast", "fallback"],
    ),
)


def _build_item_template_recipes() -> tuple[CombatTextTemplateRecipeDTO, ...]:
    recipes: list[CombatTextTemplateRecipeDTO] = []
    for entry in get_all_combat_item_action_catalog_entries():
        item_id = entry.technical.item_action_id
        recipes.extend(
            [
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.item.{item_id}.cast.single",
                    resource_type="item",
                    resource_id=item_id,
                    catalog_key=entry.key,
                    outcome="cast",
                    delivery="single",
                    pattern="{source} использует {item} на {target}.",
                    tags=["item", item_id, "cast", "single"],
                ),
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.item.{item_id}.cast.area",
                    resource_type="item",
                    resource_id=item_id,
                    catalog_key=entry.key,
                    outcome="area_result",
                    delivery="area",
                    pattern="{source} использует {item}: {target_results}.",
                    tags=["item", item_id, "area"],
                ),
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.item.{item_id}.no_resource",
                    resource_type="item",
                    resource_id=item_id,
                    catalog_key=entry.key,
                    outcome="no_resource",
                    pattern="{source} не может использовать {item}.",
                    tags=["item", item_id, "no_resource"],
                ),
            ]
        )
        for target_body in TARGET_BODIES:
            recipes.extend(
                [
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.item.{item_id}.target.hit.{target_body}",
                        resource_type="item",
                        resource_id=item_id,
                        catalog_key=entry.key,
                        outcome="hit",
                        target_body=target_body,
                        pattern="{target} получает {damage} урона от {item}",
                        tags=["item", item_id, "target", "hit", target_body],
                    ),
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.item.{item_id}.target.heal.{target_body}",
                        resource_type="item",
                        resource_id=item_id,
                        catalog_key=entry.key,
                        outcome="heal",
                        target_body=target_body,
                        pattern="{target} восстанавливает {healing} здоровья от {item}",
                        tags=["item", item_id, "target", "heal", target_body],
                    ),
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.item.{item_id}.target.apply.{target_body}",
                        resource_type="item",
                        resource_id=item_id,
                        catalog_key=entry.key,
                        outcome="apply",
                        target_body=target_body,
                        pattern="{target} получает эффект от {item}",
                        tags=["item", item_id, "target", "apply", target_body],
                    ),
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.item.{item_id}.target.miss.{target_body}",
                        resource_type="item",
                        resource_id=item_id,
                        catalog_key=entry.key,
                        outcome="miss",
                        target_body=target_body,
                        pattern="{target} избегает {item}",
                        tags=["item", item_id, "target", "miss", target_body],
                    ),
                ]
            )
    return tuple(recipes)


ITEM_SPECIFIC_TEMPLATE_RECIPES = _build_item_template_recipes()


ALL_COMBAT_TEXT_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    *TRUE_STRIKE_TEMPLATE_RECIPES,
    *BASIC_EXCHANGE_TEMPLATE_RECIPES,
    *BASIC_WEAPON_MASTERY_TEMPLATE_RECIPES,
    *GENERIC_BASIC_EXCHANGE_TEMPLATE_RECIPES,
    *DEFAULT_BASIC_EXCHANGE_TEMPLATE_RECIPES,
    *DEFAULT_FEINT_TEMPLATE_RECIPES,
    *GENERIC_FEINT_TEMPLATE_RECIPES,
    *EFFECT_TEMPLATE_RECIPES,
    *ABILITY_TEMPLATE_RECIPES,
    *ABILITY_DEFAULT_TEMPLATE_RECIPES,
    *DEATH_TEMPLATE_RECIPES,
    *TRIGGER_TEMPLATE_RECIPES,
    *GIFT_TEMPLATE_RECIPES,
    *ITEM_SPECIFIC_TEMPLATE_RECIPES,
    *ITEM_TEMPLATE_RECIPES,
)
