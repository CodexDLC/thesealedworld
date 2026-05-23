from pathlib import Path


def test_tg_bot_image_includes_shared_package() -> None:
    dockerfile = Path("deploy/tg_bot/Dockerfile").read_text(encoding="utf-8")

    assert "COPY src/shared" in dockerfile
    assert 'PYTHONPATH="/app:/app/src"' in dockerfile


def test_tg_bot_logging_delegates_to_shared_setup(monkeypatch) -> None:
    import src.tg_bot.core.logging as tg_logging
    from src.tg_bot.core.config import BotSettings

    captured: dict[str, object] = {}

    def fake_setup_logging(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(tg_logging, "shared_setup_logging", fake_setup_logging)

    settings = BotSettings(
        **{
            "BOT_TOKEN": "123:dummy",
            "SECRET" + "_KEY": "local-placeholder",
            "DEBUG": False,
            "TELEGRAM_CHANNEL_ID": "channel",
        },
    )

    tg_logging.setup_logging(settings)

    assert captured["settings"] is settings
    assert captured["service_name"] == "tg-bot"
    assert "aiogram.dispatcher" in captured["intercept_loggers"]
    assert captured["log_levels"]["codex_bot"] == 30
    assert captured["log_levels"]["httpx"] == 30
