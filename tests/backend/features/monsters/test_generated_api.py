import uuid

import pytest

from src.backend.features.monsters.api.router import (
    get_generated_monster_view_service,
    get_monster_visual_regeneration_service,
)
from src.backend.features.monsters.dto.generated_view import GeneratedMonstersResponseDTO


@pytest.mark.unit
def test_generated_monsters_route_returns_paginated_clans(client) -> None:
    class FakeService:
        async def list_generated(
            self,
            *,
            family_id=None,
            clan_id=None,
            role=None,
            include_members=True,
            limit=25,
            offset=0,
        ) -> GeneratedMonstersResponseDTO:
            assert family_id == "rat_swarm"
            assert clan_id is None
            assert role is None
            assert include_members is True
            assert limit == 10
            assert offset == 20
            return GeneratedMonstersResponseDTO(
                items=[
                    {
                        "clan_id": str(uuid.uuid4()),
                        "family_id": "rat_swarm",
                        "tier": 1,
                        "zone_id": "zone-a",
                        "name_ru": "Rats",
                        "description": "Rats",
                        "gear_score_summary": {"count": 1, "min": 7, "avg": 7.0, "max": 7, "total": 7},
                        "members": [
                            {
                                "monster_id": str(uuid.uuid4()),
                                "variant_key": "sewer_rat",
                                "role": "minion",
                                "member_tier": 1,
                                "name_ru": "Rat",
                                "threat_rating": 20,
                                "gear_score": 7,
                                "base_cost": 20,
                                "effective_cost": 4,
                            }
                        ],
                    }
                ],
                pagination={"limit": 10, "offset": 20, "total": 42, "has_more": True},
            )

    from src.backend.app import app

    app.dependency_overrides[get_generated_monster_view_service] = lambda: FakeService()
    try:
        response = client.get("/api/admin/monsters/generated?family_id=rat_swarm&limit=10&offset=20")
    finally:
        app.dependency_overrides.pop(get_generated_monster_view_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"] == {"limit": 10, "offset": 20, "total": 42, "has_more": True}
    assert payload["items"][0]["members"][0]["gear_score"] == 7


@pytest.mark.unit
def test_generated_clan_regeneration_route_returns_pending_task(client) -> None:
    class FakeService:
        async def request_clan_image(self, clan_id: str):
            assert clan_id == "clan-1"
            return {
                "task_id": "task-1",
                "entity_type": "monster_clan",
                "entity_id": "clan-1",
                "status": "pending",
                "storage_key": "monsters/generated/clans/hash.webp",
                "image_url": "/static/generated-assets/old.webp",
            }

    from src.backend.app import app

    app.dependency_overrides[get_monster_visual_regeneration_service] = lambda: FakeService()
    try:
        response = client.post("/api/admin/monsters/generated/clans/clan-1/regenerate-image")
    finally:
        app.dependency_overrides.pop(get_monster_visual_regeneration_service, None)

    assert response.status_code == 200
    assert response.json()["task_id"] == "task-1"


@pytest.mark.unit
def test_generated_member_regeneration_route_maps_missing_member_to_404(client) -> None:
    class FakeService:
        async def request_member_image(self, member_id: str):
            raise ValueError("Generated monster member not found")

    from src.backend.app import app

    app.dependency_overrides[get_monster_visual_regeneration_service] = lambda: FakeService()
    try:
        response = client.post("/api/admin/monsters/generated/members/member-1/regenerate-image")
    finally:
        app.dependency_overrides.pop(get_monster_visual_regeneration_service, None)

    assert response.status_code == 404
