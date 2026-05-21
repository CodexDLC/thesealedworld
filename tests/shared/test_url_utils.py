from src.shared.utils.url import build_absolute_url, build_public_absolute_url, build_public_base_url


def test_build_public_base_url_prefers_configured_value() -> None:
    assert (
        build_public_base_url(
            configured_base_url="https://thesealedworld.com/",
            domain_name="localhost:8000",
            request_base_url="http://testserver/",
        )
        == "https://thesealedworld.com"
    )


def test_build_public_base_url_uses_http_for_local_domain() -> None:
    assert build_public_base_url(domain_name="localhost:8000") == "http://localhost:8000"


def test_build_public_base_url_uses_https_for_public_domain() -> None:
    assert build_public_base_url(domain_name="thesealedworld.com") == "https://thesealedworld.com"


def test_build_absolute_url_keeps_existing_absolute_url() -> None:
    assert (
        build_absolute_url(base_url="https://thesealedworld.com", path_or_url="https://cdn.example/cover.webp")
        == "https://cdn.example/cover.webp"
    )


def test_build_public_absolute_url_joins_relative_path() -> None:
    assert (
        build_public_absolute_url(domain_name="thesealedworld.com", path_or_url="/news/alpha-6")
        == "https://thesealedworld.com/news/alpha-6"
    )
