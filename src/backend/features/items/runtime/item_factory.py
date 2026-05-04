from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO

if TYPE_CHECKING:
    from src.backend.features.items.services.catalog_service import ItemCatalogService


class ItemFactory:
    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        if catalog is None:
            from src.backend.features.items.services.catalog_service import ItemCatalogService

        self.catalog = catalog or ItemCatalogService.load_default()

    def generate(self, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        base = self.catalog.get_base_item(request.base_id)
        if base is None:
            raise ValueError(f"Unknown base item: {request.base_id}")

        rarity = self.catalog.get_rarity(request.rarity_tier)
        material = self._resolve_material(base.allowed_materials, request.material_id, request.rarity_tier)
        bundles = []
        for bundle_id in request.affix_bundle_ids:
            bundle = self.catalog.get_affix_bundle(bundle_id)
            if bundle is None:
                raise ValueError(f"Unknown affix bundle: {bundle_id}")
            if request.rarity_tier < bundle.min_tier:
                raise ValueError(f"Affix bundle requires tier {bundle.min_tier}: {bundle_id}")
            bundles.append(bundle)

        material_mult = material.tier_mult if material else 1.0
        power = round(base.base_power * material_mult * rarity.default_mult, 2)
        durability = round(base.base_durability * material_mult, 2)
        explicit_bonuses: dict[str, float] = {}
        tags = [*base.narrative_tags]
        if material:
            tags.extend(material.narrative_tags)

        for bundle in bundles:
            tags.extend(bundle.narrative_tags)
            for effect_id in bundle.effects:
                effect = self.catalog.get_affix_effect(effect_id)
                if effect is None:
                    raise ValueError(f"Unknown affix effect: {effect_id}")
                explicit_bonuses[effect.target_field] = (
                    explicit_bonuses.get(effect.target_field, 0.0) + effect.base_value
                )
                tags.extend(effect.narrative_tags)

        item_type = base.type or "item"
        return GeneratedItemDTO(
            template_id=f"{base.id}:{material.id if material else 'none'}:{request.rarity_tier}",
            item_type=item_type,
            rarity=rarity.enum_key,
            rarity_tier=request.rarity_tier,
            name=f"{rarity.name_ru} {base.name_ru}",
            description=self._build_mechanical_description(base.narrative_description, base.name_ru),
            base_id=base.id,
            material_id=material.id if material else None,
            affix_bundle_ids=[bundle.id for bundle in bundles],
            power=power,
            durability_max=durability,
            damage_spread=base.damage_spread,
            slot=base.slot,
            valid_slots=[base.slot, *base.extra_slots],
            implicit_bonuses=dict(base.implicit_bonuses),
            bonuses=explicit_bonuses,
            triggers=list(base.triggers),
            narrative_tags=list(dict.fromkeys(tags)),
            metadata={
                "source": request.source,
                "request_ai_text": request.request_ai_text,
                "damage_type": base.damage_type,
                "defense_type": base.defense_type,
                "related_skill": base.related_skill,
                "armor_class": base.armor_class,
            },
        )

    def _build_mechanical_description(self, base_description: str | None, base_name: str) -> str:
        if base_description:
            return base_description
        return f"{base_name}: базовый предмет без нарративного описания."

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
            return material
        for category in allowed_categories:
            material = self.catalog.get_material_for_tier(category, rarity_tier)
            if material is not None:
                return material
        return None
