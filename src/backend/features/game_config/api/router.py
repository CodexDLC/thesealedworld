from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.backend.infrastructure.game_config.manager import ConfigEntry, ConfigValidationError, GameConfigManager

router = APIRouter(prefix="/api/internal/config", tags=["game-config"])


def _manager(request: Request) -> GameConfigManager:
    return request.app.state.game_config


class SetValueBody(BaseModel):
    value: str


@router.get("")
async def list_all(request: Request) -> dict[str, list[dict]]:
    mgr = _manager(request)
    all_entries = await mgr.list_all()
    return {ns: [_entry_dict(e) for e in entries] for ns, entries in all_entries.items()}


@router.get("/{namespace}")
async def list_namespace(namespace: str, request: Request) -> list[dict]:
    mgr = _manager(request)
    if namespace not in mgr.namespaces():
        raise HTTPException(status_code=404, detail=f"Namespace {namespace!r} not registered")
    entries = await mgr.list_namespace(namespace)
    return [_entry_dict(e) for e in entries]


@router.patch("/{namespace}/{key}")
async def set_value(namespace: str, key: str, body: SetValueBody, request: Request) -> dict:
    mgr = _manager(request)
    try:
        ok = await mgr.set(namespace, key, body.value)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail=f"Key {namespace}.{key} not found")
    return {"namespace": namespace, "key": key, "value": body.value}


@router.delete("/{namespace}/{key}")
async def reset_key(namespace: str, key: str, request: Request) -> dict:
    mgr = _manager(request)
    ok = await mgr.reset(namespace, key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Key {namespace}.{key} not found")
    return {"namespace": namespace, "key": key, "reset": True}


@router.delete("/{namespace}")
async def reset_namespace(namespace: str, request: Request) -> dict:
    mgr = _manager(request)
    ok = await mgr.reset_namespace(namespace)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Namespace {namespace!r} not registered")
    return {"namespace": namespace, "reset": True}


def _entry_dict(e: ConfigEntry) -> dict:
    return {
        "key": e.key,
        "namespace": e.namespace,
        "current": e.current,
        "default": e.default,
        "value_type": e.value_type,
        "is_modified": e.current != e.default,
        "label": e.label,
        "description": e.description,
        "group": e.group,
        "unit": e.unit,
        "min_value": e.min_value,
        "max_value": e.max_value,
        "step": e.step,
        "risk": e.risk,
        "live_scope": e.live_scope,
        "tags": list(e.tags),
        "choices": list(e.choices),
        "source": e.source,
    }
