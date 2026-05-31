from __future__ import annotations


def test_arq_worker_logging_includes_runtime_instance(monkeypatch) -> None:
    import src.backend.core.arq_logging as arq_logging

    captured: dict[str, object] = {}

    def fake_setup_logging(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(arq_logging, "setup_logging", fake_setup_logging)

    arq_logging.setup_arq_worker_logging("combat-worker")

    assert captured["service_name"] == "combat-worker"
    assert captured["include_runtime_instance"] is True
    assert "arq.worker" in captured["intercept_loggers"]
