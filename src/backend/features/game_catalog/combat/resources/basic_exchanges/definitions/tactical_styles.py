from src.backend.features.game_catalog.combat.resources.basic_exchanges.schemas import (
    BasicExchangeCatalogEntryDTO,
    BasicExchangeTechnicalDTO,
)
from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatEventTextSetDTO,
    build_combat_description,
)

_BEAST_FALLBACK = CombatEventTextSetDTO(
    use=["{source} атакует {target}"],
    hit=["и попадает, нанося {damage} урона"],
    crit=["и наносит особенно сильный удар по {target}"],
    miss=["но промахивается"],
    dodge=["но {target} уклоняется"],
    parry=["но {target} отбивает удар"],
    block=["но {target} закрывается"],
)


TACTICAL_STYLE_BASIC_EXCHANGES_CATALOG: dict[str, BasicExchangeCatalogEntryDTO] = {
    # ─── SHIELD MASTERY ───────────────────────────────────────────────────────
    # Активируется когда off_hand slot содержит щит (weapon_class="shield_mastery").
    "skill_shield_mastery.off_hand": BasicExchangeCatalogEntryDTO(
        key="combat.basic_exchange.skill_shield_mastery.off_hand",
        technical=BasicExchangeTechnicalDTO(
            exchange_id="skill_shield_mastery.off_hand",
            skill_key="skill_shield_mastery",
            source_type="off_hand",
            weapon_class="shield_mastery",
            hand="off",
        ),
        descriptive=build_combat_description(
            resource_type="basic_exchange",
            resource_id="skill_shield_mastery.off_hand",
            display_name="Удар щитом",
            short_description="Атакующий толчок или удар краем щита.",
            humanoid_event_texts=CombatEventTextSetDTO(
                use=["{source} толкает {target} щитом"],
                hit=["и сбивает {target} с ритма, нанося {damage} урона"],
                crit=["и наносит мощный таранный удар, нанося {damage} урона"],
                miss=["но {target} успевает отступить"],
                dodge=["но {target} уходит с линии натиска"],
                parry=["но {target} отводит щит в сторону"],
                block=["но {target} встречает щит своей защитой"],
            ),
            beast_event_texts=_BEAST_FALLBACK,
        ),
    ),
    # ─── DUAL WIELD ───────────────────────────────────────────────────────────
    # Запись зарезервирована для случая, когда layout явно содержит skill_dual_wield
    # как off_hand weapon_class. Стандартный dual wield использует оружейный skill
    # (skill_swords, skill_fencing) — эта запись активируется только при специальных
    # build-ах, где dual_wield вынесен в оружейный слот.
    "skill_dual_wield.off_hand": BasicExchangeCatalogEntryDTO(
        key="combat.basic_exchange.skill_dual_wield.off_hand",
        technical=BasicExchangeTechnicalDTO(
            exchange_id="skill_dual_wield.off_hand",
            skill_key="skill_dual_wield",
            source_type="off_hand",
            weapon_class="dual_wield",
            hand="off",
        ),
        descriptive=build_combat_description(
            resource_type="basic_exchange",
            resource_id="skill_dual_wield.off_hand",
            display_name="Удар второй рукой",
            short_description="Удар вспомогательным оружием в стиле двойного клинка.",
            humanoid_event_texts=CombatEventTextSetDTO(
                use=["{source} переключается на второй клинок и бьёт {target}"],
                hit=["и достаёт {target} вторым оружием, нанося {damage} урона"],
                crit=["и наносит удар в незащищённую сторону {target}"],
                miss=["но {target} успевает уйти от второго клинка"],
                dodge=["но {target} скользит мимо второго оружия"],
                parry=["но {target} перехватывает второй клинок"],
                block=["но {target} прикрывается от удара"],
            ),
            beast_event_texts=_BEAST_FALLBACK,
        ),
    ),
    # ─── PARRYING ─────────────────────────────────────────────────────────────
    # Зарезервировано для контратак при успешном парировании.
    # source_type="counter" помечает это как ответный обмен, а не инициативный.
    # Активируется когда механика парирования инициирует контратаку.
    "skill_parrying.counter": BasicExchangeCatalogEntryDTO(
        key="combat.basic_exchange.skill_parrying.counter",
        technical=BasicExchangeTechnicalDTO(
            exchange_id="skill_parrying.counter",
            skill_key="skill_parrying",
            source_type="counter",
            weapon_class="parrying",
            hand="main",
        ),
        descriptive=build_combat_description(
            resource_type="basic_exchange",
            resource_id="skill_parrying.counter",
            display_name="Контратака после парирования",
            short_description="Ответный удар, открывшийся после успешного парирования.",
            humanoid_event_texts=CombatEventTextSetDTO(
                use=["{source} использует брешь в защите {target} после парирования"],
                hit=["и наносит ответный удар, причиняя {damage} урона"],
                crit=["и точно бьёт в открытую зону {target}, нанося {damage} урона"],
                miss=["но {target} успевает перегруппироваться"],
                dodge=["но {target} восстанавливает позицию"],
                parry=["но {target} отбивает ответный удар"],
                block=["но {target} успевает выставить защиту"],
            ),
            beast_event_texts=_BEAST_FALLBACK,
        ),
    ),
}
