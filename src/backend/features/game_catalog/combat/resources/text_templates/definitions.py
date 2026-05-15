from __future__ import annotations

from src.backend.features.game_catalog.combat.resources.abilities import get_all_ability_catalog_entries
from src.backend.features.game_catalog.combat.resources.effects import get_all_effect_catalog_entries
from src.backend.features.game_catalog.combat.resources.effects.schemas import EffectType
from src.backend.features.game_catalog.combat.resources.text_templates.schemas import CombatTextTemplateRecipeDTO

TARGET_BODIES = ("humanoid", "beast")

TRUE_STRIKE_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    CombatTextTemplateRecipeDTO(
        template_key="combat.feint.true_strike.hit.humanoid_to_humanoid.weapon",
        resource_type="feint",
        resource_id="true_strike",
        catalog_key="combat.feint.true_strike",
        outcome="hit",
        body_pair="humanoid_to_humanoid",
        delivery="weapon",
        pattern="{approach}, {weapon_form} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.humanoid.approach.weapon.measured",
            "weapon_form": "body.humanoid.weapon_form.skill_swords.guard_cut",
            "contact": "body.humanoid.contact_vs_humanoid.default.open_side",
            "impact": "body.humanoid.impact_vs_humanoid.hit.side",
            "result": "common.result.damage.hp",
        },
        tags=["feint", "true_strike", "weapon"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.feint.true_strike.hit.humanoid_to_beast.weapon",
        resource_type="feint",
        resource_id="true_strike",
        catalog_key="combat.feint.true_strike",
        outcome="hit",
        body_pair="humanoid_to_beast",
        delivery="weapon",
        pattern="{approach}, {weapon_form} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.humanoid.approach.weapon.measured",
            "weapon_form": "body.humanoid.weapon_form.skill_swords.cutting_line",
            "contact": "body.humanoid.contact_vs_beast.default.flank",
            "impact": "body.humanoid.impact_vs_beast.hit.flank",
            "result": "common.result.damage.hp",
        },
        tags=["feint", "true_strike", "weapon"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.feint.true_strike.hit.beast_to_humanoid.natural",
        resource_type="feint",
        resource_id="true_strike",
        catalog_key="combat.feint.true_strike",
        outcome="hit",
        body_pair="beast_to_humanoid",
        delivery="natural",
        pattern="{approach} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.beast.approach.medium.low_lunge",
            "contact": "body.beast.contact_vs_humanoid.default.open_side",
            "impact": "body.beast.impact_vs_humanoid.medium.fangs",
            "result": "common.result.damage.hp",
        },
        tags=["feint", "true_strike", "natural"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.feint.true_strike.hit.beast_to_beast.natural",
        resource_type="feint",
        resource_id="true_strike",
        catalog_key="combat.feint.true_strike",
        outcome="hit",
        body_pair="beast_to_beast",
        delivery="natural",
        pattern="{approach} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.beast.approach.medium.stalk",
            "contact": "body.beast.contact_vs_beast.default.flank",
            "impact": "body.beast.impact_vs_beast.default.flank",
            "result": "common.result.damage.hp",
        },
        tags=["feint", "true_strike", "natural"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.feint.true_strike.dodge.humanoid_to_beast.weapon",
        resource_type="feint",
        resource_id="true_strike",
        catalog_key="combat.feint.true_strike",
        outcome="dodge",
        body_pair="humanoid_to_beast",
        delivery="weapon",
        pattern="{approach}, {weapon_form} и {contact}; но {reaction}.",
        phrase_keys={
            "approach": "body.humanoid.approach.weapon.measured",
            "weapon_form": "body.humanoid.weapon_form.skill_swords.cutting_line",
            "contact": "body.humanoid.contact_vs_beast.default.flank",
            "reaction": "body.beast.reaction.dodge.side_leap",
        },
        tags=["feint", "true_strike", "weapon", "dodge"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.feint.true_strike.parry.beast_to_humanoid.natural",
        resource_type="feint",
        resource_id="true_strike",
        catalog_key="combat.feint.true_strike",
        outcome="parry",
        body_pair="beast_to_humanoid",
        delivery="natural",
        pattern="{approach} и {contact}; но {reaction}.",
        phrase_keys={
            "approach": "body.beast.approach.medium.low_lunge",
            "contact": "body.beast.contact_vs_humanoid.default.open_side",
            "reaction": "body.humanoid.reaction.parry.deflect",
        },
        tags=["feint", "true_strike", "natural", "parry"],
    ),
)

BASIC_EXCHANGE_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.basic.hit.humanoid_to_humanoid.weapon",
        resource_type="basic_exchange",
        resource_id="basic",
        catalog_key="combat.exchange.basic",
        outcome="hit",
        body_pair="humanoid_to_humanoid",
        delivery="weapon",
        pattern="{approach}, {weapon_form} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.humanoid.approach.default.weight_forward",
            "weapon_form": "body.humanoid.weapon_form.skill_swords.cutting_line",
            "contact": "body.humanoid.contact_vs_humanoid.default.body_blow",
            "impact": "body.humanoid.impact_vs_humanoid.hit.body",
            "result": "common.result.damage.hp",
        },
        tags=["exchange", "weapon"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.basic.hit.humanoid_to_beast.weapon",
        resource_type="basic_exchange",
        resource_id="basic",
        catalog_key="combat.exchange.basic",
        outcome="hit",
        body_pair="humanoid_to_beast",
        delivery="weapon",
        pattern="{approach}, {weapon_form} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.humanoid.approach.default.weight_forward",
            "weapon_form": "body.humanoid.weapon_form.skill_swords.cutting_line",
            "contact": "body.humanoid.contact_vs_beast.default.torso",
            "impact": "body.humanoid.impact_vs_beast.hit.torso",
            "result": "common.result.damage.hp",
        },
        tags=["exchange", "weapon"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.basic.hit.beast_to_humanoid.natural",
        resource_type="basic_exchange",
        resource_id="basic",
        catalog_key="combat.exchange.basic",
        outcome="hit",
        body_pair="beast_to_humanoid",
        delivery="natural",
        pattern="{approach} и {contact}; {impact}, {result}.",
        phrase_keys={
            "approach": "body.beast.approach.small.dart",
            "contact": "body.beast.contact_vs_humanoid.default.leg",
            "impact": "body.beast.impact_vs_humanoid.default.leg",
            "result": "common.result.damage.hp",
        },
        tags=["exchange", "natural"],
    ),
    CombatTextTemplateRecipeDTO(
        template_key="combat.exchange.basic.dodge.beast_to_humanoid.natural",
        resource_type="basic_exchange",
        resource_id="basic",
        catalog_key="combat.exchange.basic",
        outcome="dodge",
        body_pair="beast_to_humanoid",
        delivery="natural",
        pattern="{approach} и {contact}; но {reaction}.",
        phrase_keys={
            "approach": "body.beast.approach.small.dart",
            "contact": "body.beast.contact_vs_humanoid.default.leg",
            "reaction": "body.humanoid.reaction.dodge.sidestep",
        },
        tags=["exchange", "natural", "dodge"],
    ),
)


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
                    pattern="{source} применяет {ability} на {target}: {target_results}.",
                    tags=["ability", "cast", "single"],
                ),
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.ability.{ability_id}.cast.area",
                    resource_type="ability",
                    resource_id=ability_id,
                    catalog_key=entry.key,
                    outcome="area_result",
                    delivery="area",
                    pattern="{source} применяет {ability}: {target_results}.",
                    tags=["ability", "cast", "area"],
                ),
                CombatTextTemplateRecipeDTO(
                    template_key=f"combat.ability.{ability_id}.no_resource",
                    resource_type="ability",
                    resource_id=ability_id,
                    catalog_key=entry.key,
                    outcome="no_resource",
                    pattern="{source} пытается применить {ability}, но ресурса не хватает.",
                    tags=["ability", "no_resource"],
                ),
            ]
        )
        for target_body in TARGET_BODIES:
            recipes.extend(
                [
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.ability.{ability_id}.target.hit.{target_body}",
                        resource_type="ability",
                        resource_id=ability_id,
                        catalog_key=entry.key,
                        outcome="hit",
                        target_body=target_body,
                        pattern="{target} получает {damage} урона",
                        tags=["ability", "target", "hit", target_body],
                    ),
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.ability.{ability_id}.target.heal.{target_body}",
                        resource_type="ability",
                        resource_id=ability_id,
                        catalog_key=entry.key,
                        outcome="heal",
                        target_body=target_body,
                        pattern="{target} восстанавливает {healing} здоровья",
                        tags=["ability", "target", "heal", target_body],
                    ),
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.ability.{ability_id}.target.apply.{target_body}",
                        resource_type="ability",
                        resource_id=ability_id,
                        catalog_key=entry.key,
                        outcome="apply",
                        target_body=target_body,
                        pattern="{target} получает {effect}",
                        tags=["ability", "target", "apply", target_body],
                    ),
                    CombatTextTemplateRecipeDTO(
                        template_key=f"combat.ability.{ability_id}.target.miss.{target_body}",
                        resource_type="ability",
                        resource_id=ability_id,
                        catalog_key=entry.key,
                        outcome="miss",
                        target_body=target_body,
                        pattern="{target} избегает {ability}",
                        tags=["ability", "target", "miss", target_body],
                    ),
                ]
            )
    return tuple(recipes)


ABILITY_TEMPLATE_RECIPES = _build_ability_template_recipes()


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
        template_key="combat.trigger.style.1h_flow.proc.humanoid",
        resource_type="trigger",
        resource_id="style_1h_flow",
        catalog_key="combat.trigger.style.1h_flow",
        outcome="proc",
        target_body="humanoid",
        pattern="{source} сохраняет темп удара.",
        tags=["trigger", "style", "proc"],
    ),
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
        template_key="combat.trigger.style.offhand_attack.proc.humanoid",
        resource_type="trigger",
        resource_id="style_dual_extra",
        catalog_key="combat.trigger.style.offhand_attack",
        outcome="proc",
        target_body="humanoid",
        pattern="{source} проводит молниеносный удар второй рукой по {target}.",
        tags=["trigger", "style", "dual_wield"],
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


ALL_COMBAT_TEXT_TEMPLATE_RECIPES: tuple[CombatTextTemplateRecipeDTO, ...] = (
    *TRUE_STRIKE_TEMPLATE_RECIPES,
    *BASIC_EXCHANGE_TEMPLATE_RECIPES,
    *EFFECT_TEMPLATE_RECIPES,
    *ABILITY_TEMPLATE_RECIPES,
    *DEATH_TEMPLATE_RECIPES,
    *TRIGGER_TEMPLATE_RECIPES,
    *GIFT_TEMPLATE_RECIPES,
    *ITEM_TEMPLATE_RECIPES,
)
