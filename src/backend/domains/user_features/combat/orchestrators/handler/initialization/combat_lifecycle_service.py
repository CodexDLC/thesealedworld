# apps/game_core/modules/combats/session/initialization/combat_lifecycle_service.py
import json
import random
import time
from collections import defaultdict
from typing import Any

from loguru import logger as log

from src.backend.core.base_arq import ArqService
from src.backend.database.redis import CombatManager, ContextRedisManager
from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.domains.user_features.combat.dto import SessionDataDTO


class CombatLifecycleService:
    """
    Service for managing the lifecycle of combats sessions (RBC v3.0).
    Responsible for creation (assembling from templates) and finalization (cleanup) of the session.
    """

    def __init__(
        self,
        combat_manager: CombatManager,
        account_manager: AccountManager,
        context_manager: ContextRedisManager,
        arq_service: ArqService,  # Добавляем ARQ для запуска Хаоса
    ):
        self.combat_manager = combat_manager
        self.account_manager = account_manager
        self.context_manager = context_manager
        self.arq = arq_service

    # --- Public API ---

    async def create_battle(self, session_id: str, config: dict[str, Any]) -> None:
        """
        Main method for creating a session.
        Orchestrates loading, assembly, and persistence.
        """
        mode = config.get("mode", "standard")
        teams_payload = config.get("teams_config", {})
        ttl = config.get("ttl", 3600)

        log.info(f"Lifecycle | create_session id={session_id} mode={mode}")

        # 1. Load Templates (MGET)
        templates_map = await self._load_templates(teams_payload)

        # 2. Assemble Teams and Actors (In-Memory)
        session_data = self._assemble_session_data(session_id, mode, teams_payload, templates_map)

        # 3. Persist to Redis (via Manager)
        await self.combat_manager.create_session_batch(session_id, session_data, ttl)

        # 4. Start Chaos Relay (First Kick)
        # Ставим первую проверку через 5 минут
        await self.arq.enqueue_job("chaos_check_task", session_id, _defer_until=int(time.time() + 300))

    async def complete_session(self, session_id: str, results: dict) -> None:
        """
        Finalizes the session, cleans up Redis, and unlinks players.
        """
        log.info(f"Lifecycle | complete_session id={session_id} results={results}")

        # 1. Get participant list from Meta (actors_info)
        meta = await self.combat_manager.get_rbc_session_meta(session_id)
        participant_ids = []

        if meta and "actors_info" in meta:
            try:
                actors_info = json.loads(meta["actors_info"])
                participant_ids = list(actors_info.keys())
            except json.JSONDecodeError:
                log.error(f"Lifecycle | Failed to decode actors_info for session {session_id}")

        # 2. Cleanup Redis (queues, bullets, set history TTL)
        await self.combat_manager.cleanup_rbc_session(session_id)

        # 3. Unlink players (release them for new battles)
        if participant_ids:
            await self.account_manager.bulk_unlink_combat_session(
                [int(pid) for pid in participant_ids if pid.isdigit()]
            )

    # --- Private Helpers ---

    async def _load_templates(self, teams_payload: dict) -> dict[str, dict]:
        """
        Collects all 'ref' UUIDs and performs a single MGET request.
        """
        unique_refs = set()
        for members in teams_payload.values():
            for member in members:
                unique_refs.add(member["ref"])

        if not unique_refs:
            log.warning("Lifecycle | No participants in payload")
            return {}

        # MGET via ContextManager
        templates = await self.context_manager.get_context_batch(list(unique_refs))

        if len(templates) != len(unique_refs):
            missing = unique_refs - set(templates.keys())
            raise ValueError(f"Missing templates for refs: {missing}")

        return templates

    def _assemble_session_data(
        self, session_id: str, mode: str, teams_payload: dict, templates_map: dict
    ) -> SessionDataDTO:
        """
        Core assembly logic: cloning, naming, matchups.
        Generates structure for RBC v3.0.
        """
        final_teams = {}  # {"blue": ["id1", "id2"]}
        actors_data = {}  # {"id1": { "state": {...}, "raw": {...} }}
        all_ids = []  # ["id1", "id2", ...]
        id_to_team = {}

        # Counters for Meta
        alive_counts: dict[str, int] = defaultdict(int)
        actors_info_map = {}

        # Global Name Counter (Unique across teams)
        global_name_counter: dict[str, int] = defaultdict(int)

        # 1. Iterate through teams
        for color, members in teams_payload.items():
            team_ids = []

            for member in members:
                ref = member["ref"]
                raw_id = member["id"]
                tpl_id = str(raw_id)

                if ref not in templates_map:
                    continue

                # Increment counter for this template (Global)
                global_name_counter[tpl_id] += 1
                count = global_name_counter[tpl_id]

                # --- ID Generation Logic ---
                # Проверяем исходный тип ID (int -> player, str -> monster/template)
                if isinstance(raw_id, int):
                    final_id = f"-{tpl_id}" if mode == "shadow" and color == "red" else tpl_id
                else:
                    # Для монстров/шаблонов генерируем уникальный ID
                    final_id = tpl_id if tpl_id.startswith("-") and tpl_id[1:].isdigit() else f"{tpl_id}_{count}"

                # --- Source Data ---
                source_json = templates_map[ref]

                # Extract parts from Template (TempContextSchema)
                math_model = source_json.get("math_model", {})
                skills_data = source_json.get("skills", {})
                loadout = source_json.get("loadout", {})
                vitals = source_json.get("vitals", {})
                meta_info = source_json.get("meta", {})

                # Extract known_feints from loadout
                known_feints = loadout.get("known_feints", [])

                # Name Patching
                original_name = meta_info.get("character", {}).get("name", "Unknown")
                new_name = original_name
                if mode == "shadow" and color == "red":
                    new_name = f"Shadow {original_name}"
                elif count > 1:
                    new_name = f"{original_name} {count}"

                is_ai = not final_id.isdigit()

                # --- Build Actor Keys (RBC v3.0) ---

                # 1. :meta (JSON) - Static Info + State (Hot Data)
                actor_meta_data = {
                    "id": final_id,
                    "name": new_name,
                    "type": meta_info.get("type", "unknown"),
                    "template_id": tpl_id,
                    "is_ai": is_ai,
                    "team": color,
                    # State fields merged into meta
                    "hp": vitals.get("hp_current", 100),
                    "max_hp": vitals.get("hp_current", 100),
                    "en": vitals.get("energy_current", 100),
                    "max_en": vitals.get("energy_current", 100),
                    "tactics": 0,
                    "afk_level": 0,
                    "is_dead": False,
                    "tokens": {},
                    # Feint System
                    "feints": {"arsenal": known_feints, "hand": {}},
                }

                # 2. :raw (JSON) - Math Model
                # Берем math_model как есть (attributes, modifiers)
                raw_data = math_model.copy()

                # 3. :loadout (JSON) - Config
                # Берем loadout как есть (belt, skills, layout, tags)
                loadout_data = loadout.copy()

                # Store all keys for this actor (Unified Structure)
                actors_data[final_id] = {
                    "meta": actor_meta_data,
                    "raw": raw_data,
                    "skills": skills_data,
                    "loadout": loadout_data,
                    "statuses": {"abilities": [], "effects": []},  # NEW: Statuses container
                    "xp_buffer": {},
                    "metrics": {},
                    "explanation": {},
                }

                team_ids.append(final_id)
                all_ids.append(final_id)
                id_to_team[final_id] = color

                # Update Meta Counters
                alive_counts[color] += 1
                actors_info_map[final_id] = "player" if not is_ai else "ai"

            final_teams[color] = team_ids

        # 2. Queue Generation (Matchups) -> Global Targets
        targets_map = {}
        for my_id in all_ids:
            my_team = id_to_team[my_id]
            enemies = []
            for other_id in all_ids:
                if id_to_team[other_id] != my_team:
                    enemies.append(other_id)

            random.shuffle(enemies)
            targets_map[my_id] = enemies

        # 3. Global Meta Assembly (Optimized for Collector)
        meta = {
            "active": 1,
            "step_counter": 0,
            "start_time": int(time.time()),
            "last_activity_at": int(time.time()),  # Init last activity
            # Structure
            "teams": json.dumps(final_teams),
            "actors_info": json.dumps(actors_info_map),
            # Cache for Collector
            "dead_actors": "[]",
            "alive_counts": json.dumps(alive_counts),
            # Context
            "battle_type": mode,
            # "location_id": removed as requested
            # "rewards": removed as requested
        }

        return SessionDataDTO(meta=meta, actors=actors_data, targets=targets_map)
