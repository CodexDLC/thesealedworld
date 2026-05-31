from __future__ import annotations


def test_setup_logging_keeps_service_name_without_runtime_instance(monkeypatch) -> None:
    import src.shared.infrastructure.logging_config as logging_config

    captured: dict[str, object] = {}

    def fake_codex_setup_logging(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging_config, "codex_setup_logging", fake_codex_setup_logging)
    monkeypatch.setenv("HOSTNAME", "worker-host")

    logging_config.setup_logging(settings=object(), service_name="combat-worker")  # type: ignore[arg-type]

    assert captured["service_name"] == "combat-worker"


def test_setup_logging_can_append_runtime_instance(monkeypatch) -> None:
    import src.shared.infrastructure.logging_config as logging_config

    captured: dict[str, object] = {}

    def fake_codex_setup_logging(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging_config, "codex_setup_logging", fake_codex_setup_logging)
    monkeypatch.setenv("HOSTNAME", "worker-host")

    logging_config.setup_logging(
        settings=object(),  # type: ignore[arg-type]
        service_name="combat-worker",
        include_runtime_instance=True,
    )

    assert captured["service_name"] == "combat-worker@worker-host"
