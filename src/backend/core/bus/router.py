from collections.abc import Callable
from typing import Any

from codex_platform.streams.router import StreamRouter

FilterFunc = Callable[[dict[str, Any]], bool]
HandlerFunc = Callable[[dict[str, Any]], Any]


class GameStreamRouter(StreamRouter):
    # TODO(codex-platform): group and reply params could be upstreamed to StreamRouter.on()

    def on(
        self,
        event_type: str,
        filter_func: FilterFunc | None = None,
        group: str | None = None,
        reply: bool = False,
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        parent_decorator = super().on(event_type, filter_func)

        def decorator(handler: HandlerFunc) -> HandlerFunc:
            handler.__stream_group__ = group  # type: ignore[attr-defined]
            handler.__stream_reply__ = reply  # type: ignore[attr-defined]
            return parent_decorator(handler)

        return decorator
