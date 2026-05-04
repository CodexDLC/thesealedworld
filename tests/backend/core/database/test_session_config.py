from src.backend.config.settings import BackendSettings


def test_database_echo_is_not_tied_to_debug_by_default():
    settings = BackendSettings(debug=True)

    assert settings.debug is True
    assert settings.database_echo is False
