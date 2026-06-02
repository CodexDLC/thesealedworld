from __future__ import annotations

import re

from src.frontend.game_features.combat.view_models.screen import build_combat_screen_vm
from src.shared.schemas.combat import (
    CombatActionOptionDTO,
    CombatActorCardDTO,
    CombatActorStatSheetDTO,
    CombatActorVitalsDTO,
    CombatDashboardDTO,
    CombatDeltaDTO,
    CombatEffectBadgeDTO,
    CombatEventDTO,
    CombatExchangeStateDTO,
    CombatFeintOptionDTO,
    CombatLogActorRefDTO,
    CombatLogBadgeDTO,
    CombatLogTurnDTO,
    CombatStatSectionDTO,
    CombatStatValueDTO,
)
from tools.game_preview.fixtures import PreviewFixture


def build_fixture(name: str, params: dict[str, str]) -> PreviewFixture:
    ability_count = _ability_count(name, params)
    feint_count = _feint_count(params)
    dashboard = _dashboard(ability_count=ability_count, feint_count=feint_count)
    screen = build_combat_screen_vm(dashboard)
    context = {
        "domain": "combats",
        "char_id": 101,
        "combat_screen": screen,
        "combat_result": None,
        "combat_result_screen": None,
        "combat_outcome_screen": None,
        "background_url": "/static/images/game/combat/backgrounds/universal-combat-bg.webp",
        "status_seed": {
            "character_id": 101,
            "hp": dashboard.hero.vitals.hp_current,
            "max_hp": dashboard.hero.vitals.hp_max,
            "energy": dashboard.hero.vitals.energy_current,
            "max_energy": dashboard.hero.vitals.energy_max,
            "stamina": dashboard.hero.vitals.stamina_current,
            "max_stamina": dashboard.hero.vitals.stamina_max,
        },
    }
    return PreviewFixture(
        context=context,
        template="game/session_content_inner.html",
        title=f"Combat Preview: {ability_count} abilities",
        description="Active combat screen with token strip, ability strip, feints, attack controls, and side panels.",
        body_class="game-preview-body game-preview-body--combat",
    )


def _ability_count(name: str, params: dict[str, str]) -> int:
    if "abilities" in params:
        return max(0, int(params["abilities"]))
    match = re.search(r"(\d+)_abilities", name)
    if match:
        return max(0, int(match.group(1)))
    if name == "active":
        return 8
    raise ValueError(f"Unknown combat fixture {name!r}. Try 'active', 'active_8_abilities', or 'active_10_abilities'.")


def _feint_count(params: dict[str, str]) -> int:
    if "feints" in params:
        return max(0, min(3, int(params["feints"])))
    return 3


def _dashboard(*, ability_count: int, feint_count: int) -> CombatDashboardDTO:
    hero_ref = CombatLogActorRefDTO(id="101", name="Astra", team="team_1", actor_type="character")
    target_ref = CombatLogActorRefDTO(id="202", name="Iron Shade", team="team_2", actor_type="monster")
    hero = CombatActorCardDTO(
        actor_id="101",
        name="Astra",
        actor_type="character",
        team="team_1",
        avatar_url="/static/images/avatars/silhouette_m.webp",
        exchange_counter=5,
        committed=False,
        commit_state="idle",
        target_queue_size=1,
        vitals=CombatActorVitalsDTO(
            hp_current=78,
            hp_max=100,
            energy_current=38,
            energy_max=50,
            stamina_current=27,
            stamina_max=36,
            tactics=4,
        ),
        tokens={
            "tempo": 2,
            "hit": 5,
            "crit": 3,
            "dodge": 1,
            "parry": 4,
            "block": 2,
            "counter": 1,
            "blood": 1,
            "gift": 2,
        },
        active_effects=[
            CombatEffectBadgeDTO(
                effect_id="prep_parry_riposte",
                title="Готовый рипост",
                description="Следующее успешное парирование получает повышенный шанс контратаки.",
                duration_label="до парирования",
            ),
        ],
        feints=_feint_options(feint_count),
        stat_sheet=_stat_sheet("101", "Astra"),
    )
    target = CombatActorCardDTO(
        actor_id="202",
        name="Iron Shade",
        actor_type="monster",
        team="team_2",
        avatar_url="/static/images/avatars/veil4.webp",
        exchange_counter=5,
        committed=True,
        commit_state="committed",
        is_target=True,
        is_ai=True,
        vitals=CombatActorVitalsDTO(
            hp_current=64,
            hp_max=120,
            energy_current=22,
            energy_max=40,
            stamina_current=18,
            stamina_max=32,
        ),
        active_effects=[
            CombatEffectBadgeDTO(effect_id="dot_bleed", expires_at_exchange=7, impact={"hp": -2}),
        ],
        stat_sheet=_stat_sheet("202", "Iron Shade"),
    )
    return CombatDashboardDTO(
        session_id="preview-combat",
        turn_number=6,
        status="active",
        phase="decision",
        battle_type="duel",
        location_id="preview_arena",
        personal_turn_number=6,
        round_size=1,
        action_state="ACTION_READY",
        target_queue_size=1,
        pending_action_count=0,
        hero=hero,
        target=target,
        allies=[hero],
        enemies=[target],
        available_actions=[
            CombatActionOptionDTO(action="exchange", label="Атака", enabled=True, target_id="202"),
            *_ability_actions(ability_count),
        ],
        exchange_state=CombatExchangeStateDTO(
            pair_status="open",
            opponent_response_state="committed",
            title="ТЕКУЩИЙ РАЗМЕН",
            summary_text="Astra ищет окно для мгновенной способности перед ударом.",
            turn=6,
            source=hero_ref,
            target=target_ref,
            outcome="pending",
            badges=[CombatLogBadgeDTO(kind="tempo", value=2), CombatLogBadgeDTO(kind="hit", value=5)],
        ),
        events_delta=CombatDeltaDTO(
            turns=[
                CombatLogTurnDTO(
                    global_turn=5,
                    title="Ход 5",
                    entries=[
                        CombatEventDTO(
                            type="HIT",
                            text="Astra tags Iron Shade and gains tempo.",
                            source=hero_ref,
                            target=target_ref,
                            global_turn=5,
                        ),
                        CombatEventDTO(
                            type="TOKEN",
                            text="Iron Shade bleeds but keeps pressure.",
                            source=target_ref,
                            target=hero_ref,
                            global_turn=5,
                        ),
                    ],
                )
            ]
        ),
        log_total=2,
    )


def _ability_actions(count: int) -> list[CombatActionOptionDTO]:
    known = [
        "basic_punish_mistake",
        "basic_finish_moment",
        "basic_break_stance",
        "basic_expose_weakness",
        "basic_wipe_blood",
        "basic_grit_teeth",
        "basic_bloody_answer",
        "basic_last_push",
    ]
    actions: list[CombatActionOptionDTO] = []
    for index in range(count):
        ability_id = known[index] if index < len(known) else f"preview_gift_{index + 1}"
        actions.append(
            CombatActionOptionDTO(
                action="instant",
                label=f"Ability {index + 1}",
                enabled=index % 5 != 4,
                target_id="202",
                ability_id=ability_id,
                reason=None if index % 5 != 4 else "TOKEN_COST",
            )
        )
    return actions


def _feint_options(count: int) -> list[CombatFeintOptionDTO]:
    known = [
        CombatFeintOptionDTO(feint_id="true_strike", cost={"hit": 2}, pinned=True),
        CombatFeintOptionDTO(feint_id="guard_break", cost={"tempo": 1, "crit": 1}),
        CombatFeintOptionDTO(feint_id="low_sweep", cost={"dodge": 1}),
    ]
    return known[:count]


def _stat_sheet(actor_id: str, name: str) -> CombatActorStatSheetDTO:
    return CombatActorStatSheetDTO(
        actor_id=actor_id,
        name=name,
        sections=[
            CombatStatSectionDTO(
                key="offense",
                label="Offense",
                items=[
                    CombatStatValueDTO(key="accuracy", label="Accuracy", value=0.84, value_text="84%"),
                    CombatStatValueDTO(key="crit", label="Critical", value=0.18, value_text="18%"),
                ],
            ),
            CombatStatSectionDTO(
                key="defense",
                label="Defense",
                items=[
                    CombatStatValueDTO(key="evasion", label="Evasion", value=0.22, value_text="22%"),
                    CombatStatValueDTO(key="armor", label="Armor", value=14, value_text="14"),
                ],
            ),
        ],
        total_count=4,
    )
