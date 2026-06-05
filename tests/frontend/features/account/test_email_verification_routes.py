import importlib

import pytest


@pytest.mark.unit
def test_routes_not_registered_when_flag_off(monkeypatch):
    from src.frontend.config import settings as settings_module
    from src.frontend.core import routing_site

    monkeypatch.setattr(settings_module.settings, "enable_email_verification", False, raising=False)
    importlib.reload(routing_site)

    names = []
    for router in routing_site.SITE_ROUTERS:
        for route in router.routes:
            names.append(getattr(route, "path", ""))

    assert not any("/account/security/email/verify" in p for p in names)


@pytest.mark.unit
def test_routes_registered_when_flag_on(monkeypatch):
    from src.frontend.config import settings as settings_module
    from src.frontend.core import routing_site

    monkeypatch.setattr(settings_module.settings, "enable_email_verification", True, raising=False)
    importlib.reload(routing_site)

    names = []
    for router in routing_site.SITE_ROUTERS:
        for route in router.routes:
            names.append(getattr(route, "path", ""))

    assert any("/account/security/email/verify" in p for p in names)

    monkeypatch.setattr(settings_module.settings, "enable_email_verification", False, raising=False)
    importlib.reload(routing_site)
