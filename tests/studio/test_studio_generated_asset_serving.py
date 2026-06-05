from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from src.frontend.integrations.generated_assets import configure_generated_asset_serving


def test_studio_generated_assets_route_takes_precedence_over_static_mount(tmp_path) -> None:
    asset_path = tmp_path / "monsters" / "generated" / "members" / "rat.webp"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"webp-bytes")

    app = FastAPI()
    configure_generated_asset_serving(
        app,
        config=SimpleNamespace(
            asset_storage_backend="local",
            generated_assets_dir=tmp_path,
        ),
    )
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    response = TestClient(app).get("/static/generated-assets/monsters/generated/members/rat.webp")

    assert response.status_code == 200
    assert response.content == b"webp-bytes"
    assert response.headers["content-type"] == "image/webp"
