from fastapi_cabinet.contracts.admin import CabinetAdmin
from fastapi_cabinet.registry import CabinetRegistry


def normalize_mount_path(mount_path: str) -> str:
    normalized = "/" + mount_path.strip("/")
    return "/" if normalized == "/" else normalized


def admin_public_path(admin: CabinetAdmin, mount_path: str = "/cabinet") -> str:
    if admin.path:
        return "/" + admin.path.strip("/")
    mount = normalize_mount_path(mount_path).rstrip("/")
    return f"{mount}/{admin.key}"


def admin_route_path(admin: CabinetAdmin, mount_path: str = "/cabinet") -> str:
    public_path = admin_public_path(admin, mount_path)
    mount = normalize_mount_path(mount_path).rstrip("/")
    if public_path == mount:
        return ""
    if public_path.startswith(f"{mount}/"):
        return public_path.removeprefix(mount)
    return public_path


def resolve_active_admin(
    request_path: str,
    registry: CabinetRegistry,
    mount_path: str = "/cabinet",
) -> CabinetAdmin | None:
    normalized_request_path = "/" + request_path.strip("/")
    matches = [
        admin
        for admin in registry.all()
        if _path_matches(normalized_request_path, admin_public_path(admin, mount_path))
    ]
    if not matches:
        return None
    return max(matches, key=lambda admin: len(admin_public_path(admin, mount_path)))


def _path_matches(request_path: str, candidate_path: str) -> bool:
    normalized_candidate = "/" + candidate_path.strip("/")
    return request_path == normalized_candidate or request_path.startswith(f"{normalized_candidate}/")
