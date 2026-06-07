import uuid

from src.backend.features.game_catalog.services import GameCatalogBootstrapService
from src.backend.features.monsters.dto.generation import GeneratedClan, GeneratedMonster


def test_game_catalog_bootstrap_contains_safe_text_catalogs():
    payload = GameCatalogBootstrapService().build_bootstrap()

    assert payload.version
    assert "items" in payload.catalogs
    assert "skills" in payload.catalogs
    assert "attributes" in payload.catalogs
    assert "abilities" in payload.catalogs
    assert "feints" in payload.catalogs
    assert "effects" in payload.catalogs
    assert "triggers" in payload.catalogs
    assert "gifts" in payload.catalogs
    assert "combat_tokens" in payload.catalogs
    assert "combat_entries" in payload.catalogs
    assert "combat_text" in payload.catalogs
    assert "monster_families" in payload.catalogs
    assert "battle_axe" in payload.catalogs["items"]
    assert payload.catalogs["items"]["battle_axe"]["title"] == "Боевой топор"
    assert payload.catalogs["items"]["res_torn_pelt"]["title"] == "Дырявая шкура"
    assert payload.catalogs["items"]["res_animal_bones"]["title"] == "Кости животных"
    assert payload.catalogs["items"]["currency_dust"]["title"] == "Пыль Резидуу"
    assert "Основа всей экономики" not in payload.catalogs["items"]["currency_dust"]["description"]
    assert "skill_swords" in payload.catalogs["skills"]
    assert "strength" in payload.catalogs["attributes"]
    assert payload.catalogs["abilities"]["fireball"]["title"] == "Огненный Шар"
    expected_feints = {
        "blade_dance",
        "absolute_defense",
        "aggressive_defense",
        "active_defense",
        "answering_stance",
        "answering_series",
        "arrow_rain",
        "backstep_shot",
        "basic_seize_tempo",
        "blade_return",
        "blade_loop",
        "bind_blade",
        "blinding_shot",
        "blood_aim_crit",
        "blood_wall_crash",
        "bloody_rebuke",
        "broken_step",
        "closed_distance",
        "concussion",
        "covering_position",
        "crushing_pressure",
        "dual_blade_whirl",
        "empty_line",
        "fencing_corner_entry",
        "fencing_gap_probe",
        "fencing_hidden_entry",
        "fencing_inside_line",
        "fencing_line_flurry",
        "fencing_needle_gap",
        "fencing_precise_prick",
        "fencing_slip_guard",
        "flawless_strike",
        "foresight_parry",
        "full_defense",
        "glancing_step",
        "hard_intercept",
        "heavy_swing",
        "headshot",
        "hidden_agility",
        "hidden_strength",
        "ignore_guard",
        "lucky_break",
        "macing_armor_crush",
        "macing_break_stance",
        "macing_break_swing",
        "macing_guard_cracker",
        "macing_heavy_line",
        "macing_shock_sweep",
        "macing_skullbreaker",
        "measured_strike",
        "offhand_over",
        "open_distance",
        "open_wound",
        "open_vein",
        "pain_backstep",
        "piercing_arrow",
        "polearm_guard_intercept",
        "polearm_hook_step",
        "polearm_leg_sweep",
        "polearm_line_cleave",
        "polearm_locked_distance",
        "polearm_long_line",
        "polearm_pinning_point",
        "polearm_stunning_intercept",
        "polearm_topple_strike",
        "press_defense",
        "precise_weak_spot",
        "push_stance",
        "quiet_weak_spot",
        "ranged_covering_volley",
        "read_tactic",
        "red_line_bash",
        "reveal_intentions",
        "scarlet_riposte",
        "second_breath",
        "shield_line_bash",
        "shifting_line",
        "silent_puncture",
        "snap_shot",
        "steel_line",
        "steady_strike",
        "sword_blade_bind",
        "sword_clean_path",
        "sword_cut_angle",
        "sword_hard_bind",
        "sword_low_angle",
        "sword_measured_line",
        "sword_open_line",
        "torn_rhythm",
        "two_handed_momentum_strike",
        "two_handed_whirl",
        "wind_dance",
    }
    assert expected_feints <= set(payload.catalogs["feints"])
    assert payload.catalogs["feints"]["measured_strike"]["cost"]["tactics"] == {"hit": 3}
    assert payload.catalogs["feints"]["wind_dance"]["cost"]["tactics"] == {"dodge": 5}
    assert payload.catalogs["feints"]["second_breath"]["cost"]["tactics"] == {"parry": 5}
    assert payload.catalogs["feints"]["press_defense"]["cost"]["tactics"] == {"pressure": 3}
    assert payload.catalogs["feints"]["full_defense"]["cost"]["tactics"] == {"block": 5}
    assert payload.catalogs["feints"]["aggressive_defense"]["cost"]["tactics"] == {"hit": 2, "block": 5}
    assert payload.catalogs["feints"]["bloody_rebuke"]["cost"]["tactics"] == {"blood": 1, "hit": 2, "block": 2}
    assert payload.catalogs["feints"]["blood_wall_crash"]["cost"]["tactics"] == {"blood": 1, "hit": 3, "block": 3}
    assert payload.catalogs["feints"]["scarlet_riposte"]["cost"]["tactics"] == {"blood": 1, "block": 2, "parry": 2}
    assert payload.catalogs["feints"]["red_line_bash"]["cost"]["tactics"] == {"blood": 1, "hit": 4, "block": 2}
    assert payload.catalogs["feints"]["hidden_strength"]["cost"]["tactics"] == {"hit": 3, "parry": 3}
    assert payload.catalogs["feints"]["lucky_break"]["cost"]["tactics"] == {"crit": 5}
    assert payload.catalogs["feints"]["blade_loop"]["cost"]["tactics"] == {"hit": 6, "parry": 3, "pressure": 3}
    assert payload.catalogs["feints"]["snap_shot"]["cost"]["tactics"] == {"hit": 3}
    assert payload.catalogs["feints"]["blood_aim_crit"]["cost"]["tactics"] == {"tempo": 3, "blood": 2}
    assert payload.catalogs["feints"]["pain_backstep"]["cost"]["tactics"] == {"blood": 2, "tempo": 3}
    assert payload.catalogs["feints"]["sword_measured_line"]["cost"]["tactics"] == {"hit": 3}
    assert payload.catalogs["feints"]["sword_cut_angle"]["cost"]["tactics"] == {"hit": 3, "dodge": 5}
    assert payload.catalogs["feints"]["fencing_hidden_entry"]["cost"]["tactics"] == {"hit": 3, "dodge": 5}
    assert payload.catalogs["feints"]["fencing_inside_line"]["cost"]["tactics"] == {"hit": 3, "parry": 5}
    assert payload.catalogs["feints"]["polearm_leg_sweep"]["cost"]["tactics"] == {"hit": 3, "dodge": 5}
    assert payload.catalogs["feints"]["polearm_stunning_intercept"]["cost"]["tactics"] == {"hit": 3, "parry": 5}
    assert payload.catalogs["feints"]["macing_heavy_line"]["cost"]["tactics"] == {"hit": 3}
    assert payload.catalogs["feints"]["macing_skullbreaker"]["cost"]["tactics"] == {"hit": 3, "crit": 5}
    assert payload.catalogs["feints"]["reveal_intentions"]["cost"]["tactics"] == {"hit": 2, "tempo": 1}
    assert payload.catalogs["combat_entries"]["combat.ability.fireball"]["resource_id"] == "fireball"
    assert payload.catalogs["combat_entries"]["combat.feint.measured_strike"]["resource_id"] == "measured_strike"
    assert payload.catalogs["combat_entries"]["combat.feint.full_defense"]["resource_id"] == "full_defense"
    assert payload.catalogs["combat_entries"]["combat.ability.fireball"]["taxonomy_variants"]["humanoid"]["event_texts"][
        "area_result"
    ]
    assert payload.catalogs["combat_entries"]["combat.gift.gift_true_fire"]["resource_id"] == "gift_true_fire"
    assert payload.catalogs["combat_entries"]["combat.item.fire_grenade"]["resource_id"] == "fire_grenade"
    assert "combat.feint.true_strike" not in payload.catalogs["combat_entries"]
    assert payload.catalogs["combat_text"]["templates"]
    assert payload.catalogs["combat_text"]["resources"]["abilities"]["fireball"]["template_keys"]
    assert payload.catalogs["effects"]["dot_burn"]["title"] == "Ожог"
    assert payload.catalogs["gifts"]["gift_true_fire"]["title"] == "Истинное Пламя"
    assert payload.catalogs["combat_tokens"]["tempo"]["title"] == "Темп"
    assert payload.catalogs["combat_tokens"]["blood"]["title"] == "Кровь"
    assert payload.catalogs["combat_tokens"]["blood"]["icon"] == "token-blood"
    assert payload.catalogs["combat_tokens"]["parry"]["icon"] == "token-parry"
    assert payload.catalogs["monster_families"]["wolf_pack"]["variant_count"] > 0
    assert payload.catalogs["monster_families"]["wolf_pack"]["visual"]["image_url"].endswith("wolf_pack.svg")
    assert payload.catalogs["monster_families"]["wolf_pack"]["variants"][0]["role"] in {
        "minion",
        "veteran",
        "elite",
        "boss",
    }
    assert payload.manifest.catalogs["items"].startswith("sha256:")
    assert payload.manifest.catalogs["skills"].startswith("sha256:")
    assert payload.manifest.catalogs["abilities"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_tokens"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_entries"].startswith("sha256:")
    assert payload.manifest.catalogs["combat_text"].startswith("sha256:")
    assert payload.manifest.catalogs["monster_families"].startswith("sha256:")
    assert "stat_weights" not in payload.catalogs["skills"]["skill_swords"]


def test_game_catalog_projects_generated_monster_clans():
    clan_id = uuid.uuid4()
    clan = GeneratedClan(
        id=clan_id,
        family_id="wolf_pack",
        identity_hash="identity",
        context_identity={"tier": 1, "zone_id": "D4_0_0", "biome": "forest", "tags": ["cold"]},
        context_hash="context",
        selected_traits=[],
        title="",
        description="",
        encounter_texts={},
        generation_version=1,
        resource_version="1",
        metadata_={"flavor_content": {"mood": "hungry"}},
        members=[
            GeneratedMonster(
                id=uuid.uuid4(),
                clan_id=clan_id,
                variant_id="runner",
                member_hash="runner",
                role="minion",
                title="",
                short_description="Fast scout",
                min_tier=0,
                max_tier=1,
                mongo_actor_key="actor:wolf_pack:runner",
                active_snapshot={
                    "threat_rating": 12,
                    "scaled_attributes": {"agility": 16},
                    "scaled_skills": {"skill_fencing": 0.2},
                    "items": {},
                    "vitals": {},
                    "ai_profile": {},
                },
                metadata_={
                    "visual": {
                        "status": "fallback",
                        "image_url": "/static/images/monsters/families/wolf_pack.svg",
                        "storage_key": "monsters/generated/families/test.webp",
                    }
                },
            )
        ],
    )

    payload = GameCatalogBootstrapService().project_generated_monster_clans([clan])

    assert payload[0]["id"] == str(clan_id)
    assert payload[0]["family_key"] == "wolf_pack"
    assert payload[0]["family_label"] == "Ashen Wolves"
    assert payload[0]["title"] == "Ashen Wolves"
    assert payload[0]["summary"].startswith("Lean predators")
    assert payload[0]["danger"] == "Низкая угроза"
    assert payload[0]["visual"]["image_url"] == "/static/images/monsters/families/wolf_pack.svg"
    assert payload[0]["member_count"] == 1
    assert payload[0]["members"][0]["role_label"] == "Рядовая форма"
    assert payload[0]["members"][0]["visual"]["image_url"] == "/static/images/monsters/families/wolf_pack.svg"
    assert payload[0]["members"][0]["danger"] == "Незначительная угроза"
    assert payload[0]["members"][0]["public_stats"] == [{"label": "Ловкость", "value": 16}]
    assert payload[0]["members"][0]["public_skills"] == ["Фехтование"]
    assert "family_id" not in payload[0]
    assert "zone_id" not in payload[0]
    assert "context_hash" not in payload[0]
    assert "unique_hash" not in payload[0]
    assert "raw_tags" not in payload[0]
    assert "variant_key" not in payload[0]["members"][0]
    assert "combat_seed" not in payload[0]["members"][0]
