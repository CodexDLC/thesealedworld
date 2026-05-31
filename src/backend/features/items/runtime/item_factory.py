from __future__ import annotations

import random
from dataclasses import dataclass
from math import floor
from typing import TYPE_CHECKING, Any

from src.backend.features.items.dto.instance import (
    GeneratedItemDTO,
    ItemGenerationRequestDTO,
    RuntimeItemCombatProjectionDTO,
    RuntimeItemGenerationDebugDTO,
    RuntimeItemProjectionDTO,
)
from src.backend.features.items.resources.affix_balance import GLOBAL_AFFIX_STEPS
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG, BUNDLE_CATALOG
from src.backend.features.items.resources.affixes.pools import (
    AFFIX_POOLS_BY_ITEM_TYPE,
    AFFIX_POOLS_BY_SLOT,
    AFFIX_POOLS_BY_TAG,
)
from src.backend.features.items.resources.item_grade import AFFIX_CONTAINER_RULES, GRADE_BY_RARITY_TIER
from src.backend.features.items.resources.modifier_contracts import MODIFIER_CONTRACTS, compile_modifier_command

if TYPE_CHECKING:
    from src.backend.features.items.resources.affixes.schemas import AffixBundleDTO, AffixCatalogEntryDTO
    from src.backend.features.items.services.catalog_service import ItemCatalogService


_PREFIX_FORMS: dict[str, tuple[str, str, str, str]] = {
    "Адамантитовый": ("Адамантитовый", "Адамантитовая", "Адамантитовое", "Адамантитовые"),
    "Драконий": ("Драконий", "Драконья", "Драконье", "Драконьи"),
    "Древний": ("Древний", "Древняя", "Древнее", "Древние"),
    "Дубленый": ("Дубленый", "Дубленая", "Дубленое", "Дубленые"),
    "Дубовый": ("Дубовый", "Дубовая", "Дубовое", "Дубовые"),
    "Железнодеревянный": (
        "Железнодеревянный",
        "Железнодеревянная",
        "Железнодеревянное",
        "Железнодеревянные",
    ),
    "Ржавый": ("Ржавый", "Ржавая", "Ржавое", "Ржавые"),
    "Грязный": ("Грязный", "Грязная", "Грязное", "Грязные"),
    "Латаный": ("Латаный", "Латаная", "Латаное", "Латаные"),
    "Дырявый": ("Дырявый", "Дырявая", "Дырявое", "Дырявые"),
    "Железный": ("Железный", "Железная", "Железное", "Железные"),
    "Зачарованный": ("Зачарованный", "Зачарованная", "Зачарованное", "Зачарованные"),
    "Звездный": ("Звездный", "Звездная", "Звездное", "Звездные"),
    "Золотой": ("Золотой", "Золотая", "Золотое", "Золотые"),
    "Кристальный": ("Кристальный", "Кристальная", "Кристальное", "Кристальные"),
    "Льняной": ("Льняной", "Льняная", "Льняное", "Льняные"),
    "Мифриловый": ("Мифриловый", "Мифриловая", "Мифриловое", "Мифриловые"),
    "Небесный": ("Небесный", "Небесная", "Небесное", "Небесные"),
    "Опаленный": ("Опаленный", "Опаленная", "Опаленное", "Опаленные"),
    "Призрачный": ("Призрачный", "Призрачная", "Призрачное", "Призрачные"),
    "Прочный": ("Прочный", "Прочная", "Прочное", "Прочные"),
    "Пустотный": ("Пустотный", "Пустотная", "Пустотное", "Пустотные"),
    "Стальной": ("Стальной", "Стальная", "Стальное", "Стальные"),
    "Деревянный": ("Деревянный", "Деревянная", "Деревянное", "Деревянные"),
    "Кожаный": ("Кожаный", "Кожаная", "Кожаное", "Кожаные"),
    "Ториевый": ("Ториевый", "Ториевая", "Ториевое", "Ториевые"),
    "Толстый": ("Толстый", "Толстая", "Толстое", "Толстые"),
    "Тканый": ("Тканый", "Тканая", "Тканое", "Тканые"),
    "Чешуйчатый": ("Чешуйчатый", "Чешуйчатая", "Чешуйчатое", "Чешуйчатые"),
    "Кобальтовый": ("Кобальтовый", "Кобальтовая", "Кобальтовое", "Кобальтовые"),
}


@dataclass(slots=True)
class _ScaledItemStats:
    power: float
    durability: float
    implicit_bonuses: dict[str, float]


class ItemFactory:
    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        if catalog is None:
            from src.backend.features.items.services.catalog_service import ItemCatalogService

        self.catalog = catalog or ItemCatalogService.load_default()

    def generate(self, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        return self.generate_player_item(request)

    def generate_player_item(self, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        base = self._resolve_base(request.base_id)
        material = self._resolve_material(base.allowed_materials, request.material_id, request.rarity_tier)
        slot = self._resolve_target_slot(base, request.target_slot)
        item_grade = self._resolve_item_grade(request)
        item_tier = self._resolve_item_tier(material, request.rarity_tier)
        tier_mult = self._resolve_tier_mult(material)
        scaled = self._scale_item_stats(base, material, tier_mult)
        item_type = self._resolve_item_type(base)
        item_tags = self._build_item_tags(base, material)
        affixes, bundle_ids = self._roll_affix_set(
            request=request,
            item_grade=item_grade,
            item_type=item_type,
            slot=slot,
            item_tags=item_tags,
            item_tier=item_tier,
            tier_mult=tier_mult,
            affix_step_count=GLOBAL_AFFIX_STEPS,
        )
        all_tags = self._build_all_tags(base, material, bundle_ids, affixes)
        rarity = self.catalog.get_rarity(request.rarity_tier)
        name = self._build_player_name(base, material, rarity)
        description = self._build_player_description(base, material)
        mechanics = self._build_mechanics(
            base, material, tier_mult, base.implicit_bonuses, scaled.implicit_bonuses, affixes
        )
        metadata = self._build_metadata(
            request=request,
            base=base,
            item_grade=item_grade,
            request_ai_text=request.request_ai_text,
        )
        return self._build_generated_item(
            request=request,
            base=base,
            material=material,
            item_grade=item_grade,
            item_type=item_type,
            slot=slot,
            rarity=rarity,
            name=name,
            description=description,
            scaled=scaled,
            bundle_ids=bundle_ids,
            narrative_tags=all_tags,
            mechanics=mechanics,
            metadata=metadata,
        )

    def generate_runtime_item(self, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        base = self._resolve_base(request.base_id)
        material = self._resolve_material(base.allowed_materials, request.material_id, request.rarity_tier)
        slot = self._resolve_target_slot(base, request.target_slot)
        item_grade = self._resolve_item_grade(request)
        item_tier = self._resolve_item_tier(material, request.rarity_tier)
        tier_mult = self._resolve_tier_mult(material)
        scaled = self._scale_item_stats(base, material, tier_mult)
        item_type = self._resolve_item_type(base)
        item_tags = self._build_item_tags(base, material, extra_tags=request.extra_narrative_tags)
        affixes, bundle_ids = self._roll_affix_set(
            request=request,
            item_grade=item_grade,
            item_type=item_type,
            slot=slot,
            item_tags=item_tags,
            item_tier=item_tier,
            tier_mult=tier_mult,
            affix_step_count=request.affix_step_count or GLOBAL_AFFIX_STEPS,
        )
        all_tags = self._build_all_tags(base, material, bundle_ids, affixes, extra_tags=request.extra_narrative_tags)
        rarity = self.catalog.get_rarity(request.rarity_tier)
        name = request.presentation_name_ru or self._build_player_name(base, material, rarity)
        description = request.presentation_description or self._build_player_description(base, material)
        mechanics = self._build_mechanics(
            base, material, tier_mult, base.implicit_bonuses, scaled.implicit_bonuses, affixes
        )
        metadata = self._build_metadata(
            request=request,
            base=base,
            item_grade=item_grade,
            request_ai_text=False,
            extra_metadata={
                **request.runtime_metadata,
                "runtime_item": True,
                "affix_step_count": request.affix_step_count or GLOBAL_AFFIX_STEPS,
            },
        )
        return self._build_generated_item(
            request=request,
            base=base,
            material=material,
            item_grade=item_grade,
            item_type=item_type,
            slot=slot,
            rarity=rarity,
            name=name,
            description=description,
            scaled=scaled,
            bundle_ids=bundle_ids,
            narrative_tags=all_tags,
            mechanics=mechanics,
            metadata=metadata,
        )

    def generate_runtime_projection(
        self, request: ItemGenerationRequestDTO, *, item_id: str
    ) -> RuntimeItemProjectionDTO:
        item = self.generate_runtime_item(request)
        item = item.model_copy(update={"instance_id": item_id})
        return self.project_runtime_item(item, owner_key=_string_or_none(request.runtime_metadata.get("owner_key")))

    @staticmethod
    def project_runtime_item(item: GeneratedItemDTO, *, owner_key: str | None = None) -> RuntimeItemProjectionDTO:
        raw_affixes = item.mechanics.get("affixes")
        affixes = raw_affixes if isinstance(raw_affixes, list) else []
        material = item.mechanics.get("material") if isinstance(item.mechanics.get("material"), dict) else {}
        source_context = item.metadata.get("source_context")
        return RuntimeItemProjectionDTO(
            item_id=item.instance_id or _string_or_none(item.metadata.get("runtime_item_id")) or item.template_id,
            owner_key=owner_key or _string_or_none(item.metadata.get("owner_key")),
            base_id=item.base_id,
            item_type=item.item_type,
            slot=item.slot,
            combat=RuntimeItemCombatProjectionDTO(
                power=item.power,
                damage_spread=item.damage_spread,
                implicit_bonuses=dict(item.implicit_bonuses),
                bonuses=ItemFactory._compile_affix_bonuses(affixes),
                triggers=list(item.triggers),
                tags=list(item.narrative_tags),
                related_skill=_string_or_none(item.metadata.get("related_skill")),
            ),
            generation=RuntimeItemGenerationDebugDTO(
                material_id=_string_or_none(material.get("material_id"))
                if isinstance(material, dict)
                else item.material_id,
                item_grade=str(item.metadata.get("item_grade") or ""),
                rarity_tier=item.rarity_tier,
                affix_bundle_ids=list(item.affix_bundle_ids),
                affixes=affixes,
                natural_key=_string_or_none(
                    item.metadata.get("natural_key") or item.metadata.get("monster_equipment_key")
                ),
                source_context=dict(source_context) if isinstance(source_context, dict) else {},
            ),
        )

    def _resolve_base(self, base_id: str):
        base = self.catalog.get_base_item(base_id)
        if base is None:
            raise ValueError(f"Unknown base item: {base_id}")
        return base

    @staticmethod
    def _resolve_target_slot(base, target_slot: str | None) -> str:
        if not target_slot:
            return str(base.slot)
        valid_slots = {str(base.slot), *(str(slot) for slot in base.extra_slots)}
        if target_slot not in valid_slots:
            raise ValueError(f"Slot {target_slot!r} is not allowed for base item {base.id!r}")
        return target_slot

    @staticmethod
    def _resolve_item_grade(request: ItemGenerationRequestDTO) -> str:
        return request.item_grade or GRADE_BY_RARITY_TIER.get(request.rarity_tier, "common")

    @staticmethod
    def _resolve_item_tier(material, rarity_tier: int) -> int:
        return material.tier if material else rarity_tier

    @staticmethod
    def _resolve_tier_mult(material) -> float:
        return float(material.tier_mult) if material else 1.0

    @staticmethod
    def _resolve_item_type(base) -> str:
        return str(base.type or "item")

    def _scale_item_stats(self, base, material, tier_mult: float) -> _ScaledItemStats:
        return _ScaledItemStats(
            power=self._scale_power(base, material, tier_mult),
            durability=round(base.base_durability * tier_mult, 2),
            implicit_bonuses=self._scale_implicit_bonuses(base, material, tier_mult),
        )

    @staticmethod
    def _build_item_tags(base, material, *, extra_tags: list[str] | None = None) -> list[str]:
        tags = [*base.narrative_tags, *(material.narrative_tags if material else []), *(extra_tags or [])]
        return list(dict.fromkeys(tags))

    def _roll_affix_set(
        self,
        *,
        request: ItemGenerationRequestDTO,
        item_grade: str,
        item_type: str,
        slot: str,
        item_tags: list[str],
        item_tier: int,
        tier_mult: float,
        affix_step_count: int,
    ) -> tuple[list[dict[str, object]], list[str]]:
        affix_item_type = self._affix_item_type(item_type, slot, item_tags)
        container_rules = AFFIX_CONTAINER_RULES.get(item_grade, AFFIX_CONTAINER_RULES["common"])
        seed = request.origin_ref.seed if request.origin_ref and request.origin_ref.seed else None
        return self._fill_affixes(
            container_rules=container_rules,
            item_type=affix_item_type,
            slot=slot,
            item_tags=item_tags,
            item_tier=item_tier,
            tier_mult=tier_mult,
            forced_bundle_ids=request.affix_bundle_ids,
            forced_affix_ids=request.forced_affix_ids,
            allowed_affix_ids=request.allowed_affix_ids,
            affix_count=request.affix_count,
            rng=random.Random(seed),
            affix_step_count=affix_step_count,
        )

    @staticmethod
    def _build_all_tags(
        base,
        material,
        bundle_ids: list[str],
        affixes: list[dict[str, object]],
        *,
        extra_tags: list[str] | None = None,
    ) -> list[str]:
        bundle_narrative_tags: list[str] = []
        for bundle_id in bundle_ids:
            bundle = BUNDLE_CATALOG.get(bundle_id)
            if bundle:
                bundle_narrative_tags.extend(bundle.tags)

        affix_narrative_tags: list[str] = []
        for affix in affixes:
            tags = affix.pop("_narrative_tags", [])
            if isinstance(tags, list):
                affix_narrative_tags.extend(tags)

        return list(
            dict.fromkeys(
                [
                    *base.narrative_tags,
                    *(material.narrative_tags if material else []),
                    *(extra_tags or []),
                    *bundle_narrative_tags,
                    *affix_narrative_tags,
                ]
            )
        )

    def _build_player_name(self, base, material, rarity) -> str:
        return self._build_instance_name(
            base.name_ru,
            rarity_name=rarity.name_ru,
            material_name=material.name_ru if material else None,
            material_prefix=material.name_prefix_ru if material else None,
        )

    def _build_player_description(self, base, material) -> str:
        return self._build_deterministic_description(
            base_description=base.narrative_description,
            base_name=base.name_ru,
            material_description=material.narrative_description if material else None,
        )

    @staticmethod
    def _build_mechanics(
        base,
        material,
        tier_mult: float,
        base_implicit: dict[str, float],
        scaled_implicit: dict[str, float],
        affixes: list[dict[str, object]],
    ) -> dict[str, object]:
        mechanics: dict[str, object] = {
            "implicit_bonuses_base": dict(base_implicit),
            "implicit_bonuses": scaled_implicit,
            "material": {
                "material_id": material.id if material else None,
                "tier_mult": tier_mult,
                "tags": list(material.narrative_tags) if material else [],
            },
            "affixes": affixes,
            "sockets": [],
        }
        for key in ("ammo_charge_base", "ammo_charge_skill_bonus", "ammo_effect_payload"):
            value = getattr(base, key, None)
            if value is not None:
                mechanics[key] = ItemFactory._copy_mechanics_value(value)
        return mechanics

    @staticmethod
    def _copy_mechanics_value(value: Any) -> object:
        if isinstance(value, dict):
            return {str(key): ItemFactory._copy_mechanics_value(nested) for key, nested in value.items()}
        if isinstance(value, list):
            return [ItemFactory._copy_mechanics_value(nested) for nested in value]
        return value

    @staticmethod
    def _build_metadata(
        *,
        request: ItemGenerationRequestDTO,
        base,
        item_grade: str,
        request_ai_text: bool,
        extra_metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "source": request.source,
            "source_context": request.source_context,
            "request_ai_text": request_ai_text,
            "damage_type": base.damage_type,
            "defense_type": base.defense_type,
            "related_skill": base.related_skill,
            "armor_class": base.armor_class,
            "item_grade": item_grade,
            **(extra_metadata or {}),
        }

    @staticmethod
    def _build_generated_item(
        *,
        request: ItemGenerationRequestDTO,
        base,
        material,
        item_grade: str,
        item_type: str,
        slot: str,
        rarity,
        name: str,
        description: str,
        scaled: _ScaledItemStats,
        bundle_ids: list[str],
        narrative_tags: list[str],
        mechanics: dict[str, object],
        metadata: dict[str, object],
    ) -> GeneratedItemDTO:
        return GeneratedItemDTO(
            template_id=f"{base.id}:{material.id if material else 'none'}:{item_grade}",
            item_type=item_type,
            rarity=rarity.enum_key,
            rarity_tier=request.rarity_tier,
            name=name,
            description=description,
            base_id=base.id,
            material_id=material.id if material else None,
            affix_bundle_ids=bundle_ids,
            power=scaled.power,
            durability_max=scaled.durability,
            damage_spread=base.damage_spread,
            slot=slot,
            valid_slots=[base.slot, *base.extra_slots],
            implicit_bonuses=scaled.implicit_bonuses,
            bonuses={},
            triggers=list(base.triggers),
            narrative_tags=narrative_tags,
            mechanics=mechanics,
            metadata=metadata,
        )

    @staticmethod
    def _compile_affix_bonuses(affixes: list[object]) -> dict[str, str]:
        bonuses: dict[str, str] = {}
        for raw_affix in affixes:
            if not isinstance(raw_affix, dict):
                continue
            affix_id = _string_or_none(raw_affix.get("affix_id"))
            if affix_id is None:
                continue
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                continue
            contract = MODIFIER_CONTRACTS.get(entry.technical.modifier_id)
            if contract is None:
                continue
            value = _float_or_none(raw_affix.get("value"))
            if value is None:
                continue
            bonuses[contract.target_field] = compile_modifier_command(contract, value)
        return bonuses

    @staticmethod
    def _scale_power(base, material, tier_mult: float) -> float:
        if base.id == "belt":
            material_tier = int(material.tier) if material else 0
            return float(max(0, int(base.base_power) * max(1, material_tier + 1)))
        return round(base.base_power * tier_mult, 2)

    @staticmethod
    def _scale_implicit_bonuses(base, material, tier_mult: float) -> dict[str, float]:
        material_tier = int(material.tier) if material else 0
        scaled: dict[str, float] = {}
        for key, value in base.implicit_bonuses.items():
            numeric = float(value)
            if base.id == "belt" and key == "quick_slot_capacity":
                scaled[key] = float(min(8, max(0, int(numeric) + material_tier)))
                continue
            scaled[key] = round(numeric * tier_mult, 4)
        return scaled

    @staticmethod
    def _affix_item_type(item_type: str, slot: str, tags: list[str]) -> str:
        if slot == "belt_accessory":
            return "belt"
        if slot == "off_hand" and "shield" in tags:
            return "shield"
        return item_type

    def _fill_affixes(
        self,
        *,
        container_rules: dict[str, object],
        item_type: str,
        slot: str,
        item_tags: list[str],
        item_tier: int,
        tier_mult: float,
        forced_bundle_ids: list[str],
        rng: random.Random,
        forced_affix_ids: list[str] | None = None,
        allowed_affix_ids: list[str] | None = None,
        affix_count: int | None = None,
        affix_step_count: int = GLOBAL_AFFIX_STEPS,
    ) -> tuple[list[dict[str, object]], list[str]]:
        raw_max = container_rules.get("max")
        max_count = int(raw_max) if isinstance(raw_max, (int, str)) else 0
        raw_min = container_rules.get("min")
        min_count = int(raw_min) if isinstance(raw_min, (int, str)) else 0
        raw_bundle_chance = container_rules.get("bundle_chance")
        bundle_chance = float(raw_bundle_chance) if isinstance(raw_bundle_chance, (int, float, str)) else 0.0
        raw_bundle_sizes = container_rules.get("bundle_sizes")
        allowed_bundle_sizes: list[int] = list(raw_bundle_sizes) if isinstance(raw_bundle_sizes, list) else []  # type: ignore[arg-type]
        if affix_count is not None:
            min_count = max(0, affix_count)
            max_count = min_count

        if max_count == 0:
            return [], []

        filled: list[dict[str, object]] = []
        bundle_ids_used: list[str] = []
        chosen_affix_ids: set[str] = set()

        forced_pool = set(
            self._pool_for_item(
                item_type,
                slot,
                item_tags,
                item_tier,
                already_chosen=set(),
                allowed_affix_ids=allowed_affix_ids,
            )
        )
        for affix_id in forced_affix_ids or []:
            if affix_id in chosen_affix_ids or affix_id not in forced_pool or len(filled) >= max_count:
                continue
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                continue
            rolled = self._roll_affix(entry, tier_mult, rng, item_tier=item_tier, affix_step_count=affix_step_count)
            rolled["source"] = "forced"
            rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
            filled.append(rolled)
            chosen_affix_ids.add(affix_id)

        # Forced bundles from request (treated as boss/forced drops)
        for bundle_id in forced_bundle_ids:
            bundle = BUNDLE_CATALOG.get(bundle_id)
            if bundle is None:
                continue
            if not self._bundle_matches_item(bundle, item_type, item_tags, item_tier):
                continue
            added_from_bundle = False
            for affix_id in bundle.affix_ids:
                if affix_id in chosen_affix_ids or len(filled) >= max_count:
                    continue
                if allowed_affix_ids and affix_id not in allowed_affix_ids:
                    continue
                entry = AFFIX_CATALOG.get(affix_id)
                if entry is None or not self._affix_matches_item(entry, item_tags, item_tier):
                    continue
                rolled = self._roll_affix(entry, tier_mult, rng, item_tier=item_tier, affix_step_count=affix_step_count)
                rolled["source"] = f"bundle:{bundle_id}"
                rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
                filled.append(rolled)
                chosen_affix_ids.add(affix_id)
                added_from_bundle = True
            if added_from_bundle and bundle_id not in bundle_ids_used:
                bundle_ids_used.append(bundle_id)

        # Bundle chance roll (only when no forced bundles)
        if not forced_bundle_ids and bundle_chance > 0 and rng.random() < bundle_chance:
            candidates = [
                b
                for b in BUNDLE_CATALOG.values()
                if b.size in allowed_bundle_sizes and self._bundle_matches_item(b, item_type, item_tags, item_tier)
            ]
            if candidates:
                bundle = rng.choice(candidates)
                for affix_id in bundle.affix_ids:
                    if affix_id in chosen_affix_ids or len(filled) >= max_count:
                        continue
                    if allowed_affix_ids and affix_id not in allowed_affix_ids:
                        continue
                    entry = AFFIX_CATALOG.get(affix_id)
                    if entry is None or not self._affix_matches_item(entry, item_tags, item_tier):
                        continue
                    rolled = self._roll_affix(
                        entry,
                        tier_mult,
                        rng,
                        item_tier=item_tier,
                        affix_step_count=affix_step_count,
                    )
                    rolled["source"] = f"bundle:{bundle.id}"
                    rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
                    filled.append(rolled)
                    chosen_affix_ids.add(affix_id)
                bundle_ids_used.append(bundle.id)

        # Fill singles to reach a target between min_count and max_count
        target = rng.randint(min_count, max_count) if min_count <= max_count else max_count
        while len(filled) < target:
            pool = self._pool_for_item(
                item_type,
                slot,
                item_tags,
                item_tier,
                chosen_affix_ids,
                allowed_affix_ids=allowed_affix_ids,
            )
            if not pool:
                break
            affix_id = rng.choice(pool)
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                chosen_affix_ids.add(affix_id)
                continue
            rolled = self._roll_affix(entry, tier_mult, rng, item_tier=item_tier, affix_step_count=affix_step_count)
            rolled["source"] = f"single:{entry.group}"
            rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
            filled.append(rolled)
            chosen_affix_ids.add(affix_id)

        return filled, bundle_ids_used

    @staticmethod
    def _roll_affix(
        entry: AffixCatalogEntryDTO,
        tier_mult: float,
        rng: random.Random,
        *,
        item_tier: int,
        affix_step_count: int = GLOBAL_AFFIX_STEPS,
    ) -> dict[str, object]:
        profile = entry.technical.roll_profile
        step_base = entry.technical.base_value * tier_mult
        lo = max(0.0, 1.0 - profile.step_spread)
        hi = 1.0 + profile.step_spread
        step_count = max(1, affix_step_count)
        step_mults = [rng.uniform(lo, hi) for _ in range(step_count)]
        step_roll_total = sum(step_mults)
        raw_value = step_base * step_roll_total
        value = _round_value(raw_value, profile.rounding, profile.round_digits)

        max_total = step_count * (1.0 + profile.step_spread)
        min_total = step_count * max(0.0, 1.0 - profile.step_spread)
        roll_quality = (
            round(max(0.0, min(1.0, (step_roll_total - min_total) / (max_total - min_total))), 4)
            if max_total > min_total
            else 0.5
        )

        return {
            "affix_id": entry.id,
            "value": value,
            "tier": item_tier,
            "source": "",
            "roll_quality": roll_quality,
            "roll": {"step_count": step_count, "step_roll_total": round(step_roll_total, 4)},
        }

    @staticmethod
    def _pool_for_item(
        item_type: str,
        slot: str,
        item_tags: list[str],
        item_tier: int,
        already_chosen: set[str],
        allowed_affix_ids: list[str] | None = None,
    ) -> list[str]:
        type_pool = set(AFFIX_POOLS_BY_ITEM_TYPE.get(item_type, []))

        slot_pool = set(AFFIX_POOLS_BY_SLOT.get(slot, []))
        if slot_pool:
            candidate = type_pool & slot_pool
            if candidate:
                type_pool = candidate

        tag_union: set[str] = set()
        for tag in item_tags:
            if tag in AFFIX_POOLS_BY_TAG:
                tag_union.update(AFFIX_POOLS_BY_TAG[tag])
        if tag_union:
            candidate = type_pool & tag_union
            if candidate:
                type_pool = candidate
        if allowed_affix_ids:
            type_pool &= set(allowed_affix_ids)

        result: list[str] = []
        for affix_id in type_pool:
            if affix_id in already_chosen:
                continue
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                continue
            if not ItemFactory._affix_matches_item(entry, item_tags, item_tier):
                continue
            result.append(affix_id)
        return result

    @staticmethod
    def _bundle_matches_item(
        bundle: AffixBundleDTO,
        item_type: str,
        item_tags: list[str],
        item_tier: int,
    ) -> bool:
        if item_type not in bundle.allowed_item_types:
            return False
        if bundle.min_item_tier > item_tier:
            return False
        return all(
            (entry := AFFIX_CATALOG.get(affix_id)) is not None
            and ItemFactory._affix_matches_item(entry, item_tags, item_tier)
            for affix_id in bundle.affix_ids
        )

    @staticmethod
    def _affix_matches_item(entry: AffixCatalogEntryDTO, item_tags: list[str], item_tier: int) -> bool:
        if entry.technical.min_item_tier > item_tier:
            return False
        return not entry.technical.required_item_tags or all(
            tag in item_tags for tag in entry.technical.required_item_tags
        )

    def _resolve_material(
        self,
        allowed_categories: list[str],
        material_id: str | None,
        rarity_tier: int,
    ):
        if material_id:
            material = self.catalog.get_material(material_id)
            if material is None:
                raise ValueError(f"Unknown material: {material_id}")
            if allowed_categories and material.category not in allowed_categories:
                raise ValueError(
                    f"Material {material_id!r} category {material.category!r} is not allowed for item "
                    f"categories {allowed_categories!r}"
                )
            return material
        for category in allowed_categories:
            material = self.catalog.get_material_for_tier(category, rarity_tier)
            if material is not None:
                return material
        return None

    def _build_instance_name(
        self,
        base_name: str,
        rarity_name: str,
        material_name: str | None,
        material_prefix: str | None = None,
    ) -> str:
        if material_prefix:
            return f"{self._agree_prefix(material_prefix, base_name)} {base_name.lower()}"
        if material_name:
            return f"{material_name}: {base_name}"
        return f"{rarity_name} {base_name}"

    @staticmethod
    def _agree_prefix(prefix: str, base_name: str) -> str:
        variants = _PREFIX_FORMS.get(prefix)
        if variants is None:
            return prefix
        normalized = base_name.strip().lower()
        if normalized.endswith(("и", "ы")):
            return variants[3]
        if normalized.endswith(("а", "я")):
            return variants[1]
        if normalized.endswith(("о", "е")):
            return variants[2]
        return variants[0]

    @staticmethod
    def _build_deterministic_description(
        base_description: str | None,
        base_name: str,
        material_description: str | None,
    ) -> str:
        if base_description:
            return base_description
        if material_description:
            base_lower = base_name[0].lower() + base_name[1:] if base_name else ""
            sentence = f"{material_description} {base_lower}."
            return sentence[0].upper() + sentence[1:]
        return f"{base_name}: предмет без описания."


def _round_value(value: float, rounding: str, round_digits: int) -> float:
    if rounding == "floor_int":
        return float(floor(value))
    if rounding == "round_int":
        return float(round(value))
    return round(value, round_digits)


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float | str):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None
