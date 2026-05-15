from src.backend.core.database import Base, model_imports


def test_backend_metadata_includes_chat_schema_models() -> None:
    _ = model_imports

    assert "chat.chat_messages" in Base.metadata.tables
    assert "chat.chat_sessions" in Base.metadata.tables
    assert "chat.chat_session_messages" in Base.metadata.tables


def test_backend_metadata_does_not_own_site_auth_models() -> None:
    _ = model_imports

    assert "auth_users" not in Base.metadata.tables
    assert "auth_refresh_tokens" not in Base.metadata.tables
    assert "site.auth_users" not in Base.metadata.tables
    assert "site.auth_refresh_tokens" not in Base.metadata.tables


def test_character_user_id_has_no_site_auth_foreign_key() -> None:
    _ = model_imports

    character_table = Base.metadata.tables["characters"]
    assert not character_table.c.user_id.foreign_keys
