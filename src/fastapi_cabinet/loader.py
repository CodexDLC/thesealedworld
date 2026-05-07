from collections.abc import Sequence
from importlib import import_module
from inspect import signature
from types import ModuleType

from fastapi_cabinet.exceptions import CabinetModuleLoadError
from fastapi_cabinet.site import CabinetSite

CabinetModuleRef = str | ModuleType


def load_cabinet_modules(modules: Sequence[CabinetModuleRef], site: CabinetSite) -> tuple[ModuleType, ...]:
    loaded: list[ModuleType] = []
    for ref in modules:
        try:
            module = import_module(ref) if isinstance(ref, str) else ref
        except ImportError as exc:
            raise CabinetModuleLoadError(f"Could not import cabinet module {ref!r}.") from exc
        hook = getattr(module, "register_cabinet", None)
        if hook is not None:
            if not callable(hook):
                raise CabinetModuleLoadError(
                    f"Cabinet module {module.__name__!r} defines register_cabinet, but it is not callable."
                )
            try:
                parameters = signature(hook).parameters
            except (TypeError, ValueError) as exc:
                raise CabinetModuleLoadError(
                    f"Cabinet module {module.__name__!r} has an invalid register_cabinet hook."
                ) from exc
            if len(parameters) != 1:
                raise CabinetModuleLoadError(
                    f"Cabinet module {module.__name__!r} register_cabinet hook must accept exactly one registry."
                )
            hook(site.registry)
        loaded.append(module)
    return tuple(loaded)
