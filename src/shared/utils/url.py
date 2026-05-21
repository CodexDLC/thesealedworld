from __future__ import annotations

from urllib.parse import urlsplit


def build_public_base_url(
    *,
    configured_base_url: str = "",
    domain_name: str = "",
    request_base_url: str = "http://testserver/",
) -> str:
    configured = configured_base_url.strip()
    if configured:
        return configured.rstrip("/")

    domain = domain_name.strip()
    if domain:
        if urlsplit(domain).scheme in {"http", "https"}:
            return domain.rstrip("/")
        scheme = "http" if _is_local_domain(domain) else "https"
        return f"{scheme}://{domain}".rstrip("/")

    return request_base_url.rstrip("/")


def build_absolute_url(*, base_url: str, path_or_url: str) -> str:
    if not path_or_url:
        return ""
    if urlsplit(path_or_url).scheme:
        return path_or_url

    path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
    return f"{base_url.rstrip('/')}{path}"


def build_public_absolute_url(
    *,
    path_or_url: str,
    configured_base_url: str = "",
    domain_name: str = "",
    request_base_url: str = "http://testserver/",
) -> str:
    base_url = build_public_base_url(
        configured_base_url=configured_base_url,
        domain_name=domain_name,
        request_base_url=request_base_url,
    )
    return build_absolute_url(base_url=base_url, path_or_url=path_or_url)


def _is_local_domain(domain: str) -> bool:
    return domain.startswith(("localhost", "127.0.0.1"))
