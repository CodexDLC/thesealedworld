from src.backend.core.database import Base, model_imports


def test_backend_metadata_includes_chat_schema_models() -> None:
    _ = model_imports

    assert "chat.chat_threads" in Base.metadata.tables
    assert "chat.chat_thread_members" in Base.metadata.tables
    assert "chat.chat_message_index" in Base.metadata.tables
    assert "chat.chat_messages" not in Base.metadata.tables
    assert "chat.chat_sessions" not in Base.metadata.tables
    assert "chat.chat_session_messages" not in Base.metadata.tables


def test_backend_metadata_includes_item_generated_templates() -> None:
    _ = model_imports

    assert "item_generated_templates" in Base.metadata.tables
    assert "generated_template_id" in Base.metadata.tables["item_instances"].c


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


def test_backend_metadata_includes_character_location_knowledge() -> None:
    _ = model_imports

    table = Base.metadata.tables["character_location_knowledge"]
    assert "character_id" in table.c
    assert "loc_id" in table.c
    assert "movement_xp_spent" in table.c
    assert "scouting_xp_cap" in table.c
