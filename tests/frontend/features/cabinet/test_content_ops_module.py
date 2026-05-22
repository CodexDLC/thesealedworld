from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_cabinet import include_cabinet
from src.frontend.cabinet import CABINET_MODULES
from src.frontend.features.cabinet.modules.content_ops.cabinet import (
    ContentOpsAdmin,
    _filter_monster_clans,
)
from src.frontend.integrations.backend_api.admin_monsters import (
    AdminGeneratedMonsterClan,
    AdminGeneratedMonsterMember,
    AdminMonsterVisual,
)


def test_content_ops_admin_declares_operational_sections() -> None:
    assert ContentOpsAdmin.key == "content_ops"
    assert ContentOpsAdmin.path == "/admin/content-ops"
    assert ContentOpsAdmin.label == "Content"
    assert ContentOpsAdmin.group_label == "Content"
    assert [item.key for item in ContentOpsAdmin.sidebar] == ["overview", "monsters"]
    assert [item.path for item in ContentOpsAdmin.sidebar] == [
        "/admin/content-ops",
        "/admin/content-ops/monster-browser",
    ]
    assert "monster-browser" in ContentOpsAdmin.action_routes
    assert "monster-detail" in ContentOpsAdmin.action_routes


def test_content_ops_filters_monsters_by_domain_safe_fields() -> None:
    rat = _clan("rat-clan", family="rats", storage="s3", roles=("scout", "brute"), missing_member=False)
    spider = _clan("spider-clan", family="spiders", storage="local", roles=("caster",), missing_member=True)

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "spiders", "role": "", "storage_backend": "", "missing_image": ""},
    )
    assert [clan.clan_id for clan in filtered] == ["spider-clan"]

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "", "role": "scout", "storage_backend": "s3", "missing_image": ""},
    )
    assert [clan.clan_id for clan in filtered] == ["rat-clan"]

    filtered = _filter_monster_clans(
        [rat, spider],
        {"family_id": "", "role": "", "storage_backend": "", "missing_image": "1"},
    )
    assert [clan.clan_id for clan in filtered] == ["spider-clan"]


def test_content_ops_custom_pages_render_operational_surfaces() -> None:
    app = FastAPI()
    include_cabinet(app, modules=CABINET_MODULES, mount_path="/admin")
    client = TestClient(app)

    monsters = client.get("/admin/content-ops/monster-browser")
    assert monsters.status_code == 200
    assert "Generated monsters" in monsters.text
    assert "Missing image" in monsters.text


def _clan(
    clan_id: str,
    *,
    family: str,
    storage: str,
    roles: tuple[str, ...],
    missing_member: bool,
) -> AdminGeneratedMonsterClan:
    return AdminGeneratedMonsterClan(
        clan_id=clan_id,
        family_id=family,
        tier=1,
        zone_id="zone",
        name_ru=clan_id,
        description="",
        visual=AdminMonsterVisual(image_url="/static/generated-assets/clan.webp", storage_backend=storage),
        members=[
            AdminGeneratedMonsterMember(
                monster_id=f"{clan_id}-{role}",
                variant_key=role,
                role=role,
                member_tier=1,
                name_ru=role,
                threat_rating=1,
                gear_score=1,
                visual=AdminMonsterVisual(
                    image_url="" if missing_member and index == 0 else "/static/generated-assets/member.webp",
                    storage_backend=storage,
                ),
            )
            for index, role in enumerate(roles)
        ],
    )
