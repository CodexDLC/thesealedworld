from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.backend.features.npc.catalog import NpcDefinition, get_npc_definition

if TYPE_CHECKING:
    from src.backend.features.npc.models import CharacterNpcState
    from src.backend.features.npc.repositories import NpcStateRepository


@dataclass(frozen=True, slots=True)
class DialogueNpcContext:
    definition: NpcDefinition
    reputation: int
    affinity: int
    flags: dict[str, Any]
    counters: dict[str, int]

    def flatten(self) -> dict[str, Any]:
        flat: dict[str, Any] = {
            "npc_key": self.definition.npc_key,
            "npc_reputation": int(self.reputation),
            "npc_affinity": int(self.affinity),
        }
        for key, value in self.flags.items():
            flat[f"npc_flag_{key}"] = int(bool(value)) if isinstance(value, bool) else value
        for key, value in self.counters.items():
            flat[f"npc_counter_{key}"] = int(value)
        return flat


class NpcService:
    def __init__(self, repository: NpcStateRepository) -> None:
        self.repository = repository

    def get_definition(self, npc_key: str) -> NpcDefinition:
        definition = get_npc_definition(npc_key)
        if definition is None:
            raise ValueError(f"Unknown npc_key: {npc_key}")
        return definition

    async def get_or_create_state(self, *, character_id: int, npc_key: str) -> CharacterNpcState:
        self.get_definition(npc_key)
        state = await self.repository.get_or_create_state(character_id=character_id, npc_key=npc_key)
        await self.repository.commit()
        return state

    async def load_dialogue_context(self, *, character_id: int, npc_key: str) -> DialogueNpcContext:
        definition = self.get_definition(npc_key)
        state = await self.repository.get_or_create_state(character_id=character_id, npc_key=npc_key)
        await self.repository.commit()
        return DialogueNpcContext(
            definition=definition,
            reputation=int(state.reputation or 0),
            affinity=int(state.affinity or 0),
            flags=dict(state.flags or {}),
            counters={str(key): int(value) for key, value in dict(state.counters or {}).items()},
        )

    async def apply_effects(
        self,
        *,
        character_id: int,
        npc_key: str,
        effects: list[dict[str, Any]],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not effects:
            return {"applied": False, "duplicate": False, "effect_count": 0}

        self.get_definition(npc_key)
        try:
            claimed = await self.repository.claim_effect_application(
                character_id=character_id,
                npc_key=npc_key,
                idempotency_key=idempotency_key,
                effect_count=len(effects),
            )
            if not claimed:
                await self.repository.rollback()
                return {"applied": False, "duplicate": True, "effect_count": 0}

            state = await self.repository.get_or_create_state(
                character_id=character_id, npc_key=npc_key, for_update=True
            )
            now = datetime.now(UTC)
            flags = dict(state.flags or {})
            counters = {str(key): int(value) for key, value in dict(state.counters or {}).items()}
            reputation = int(state.reputation or 0)
            affinity = int(state.affinity or 0)

            for effect in effects:
                effect_type = str(effect.get("type") or "")
                if effect_type == "npc.set_flag":
                    flags[str(effect["flag"])] = bool(effect.get("value", True))
                elif effect_type == "npc.unset_flag":
                    flags.pop(str(effect["flag"]), None)
                elif effect_type == "npc.bump_counter":
                    key = str(effect["counter"])
                    counters[key] = int(counters.get(key, 0)) + int(effect.get("amount", 1))
                elif effect_type == "npc.adjust_reputation":
                    reputation += int(effect.get("amount", 0))
                elif effect_type == "npc.adjust_affinity":
                    affinity += int(effect.get("amount", 0))
                else:
                    raise RuntimeError(f"Unsupported NPC effect: {effect_type}")

            state.flags = flags
            state.counters = counters
            state.reputation = reputation
            state.affinity = affinity
            state.last_interaction_at = now
            state.version = int(state.version or 0) + 1
            await self.repository.commit()
            return {
                "applied": True,
                "duplicate": False,
                "effect_count": len(effects),
                "reputation": reputation,
                "affinity": affinity,
                "flags": flags,
                "counters": counters,
                "last_interaction_at": now.isoformat(),
                "version": state.version,
            }
        except Exception:
            await self.repository.rollback()
            raise
