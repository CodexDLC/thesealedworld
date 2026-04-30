import pytest
from src.backend.core.bus.router import GameStreamRouter
from codex_platform.streams import StreamRouter

@pytest.mark.unit
class TestGameStreamRouter:
    def test_router_is_alias(self):
        assert GameStreamRouter is StreamRouter

    def test_router_on_usage(self):
        router = GameStreamRouter()

        @router.on("test_event", group="test_group", reply=True)
        def handle_event(payload):
            return payload

        assert "test_event" in router.handlers
