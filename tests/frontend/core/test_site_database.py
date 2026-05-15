from src.frontend.core.database import Base, load_orm_models


def test_site_database_metadata_registers_auth_models() -> None:
    load_orm_models()

    assert Base.metadata.schema == "site"
    assert "site.auth_users" in Base.metadata.tables
    assert "site.auth_refresh_tokens" in Base.metadata.tables
