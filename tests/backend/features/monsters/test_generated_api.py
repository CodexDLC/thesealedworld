import uuid

import pytest

from src.backend.features.monsters.api.router import get_generated_monster_view_service
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
