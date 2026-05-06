from pathlib import Path

CHAT_TEMPLATE = Path("src/frontend/templates/shared/chat/main.html")
CHAT_LAYOUT_CSS = Path("src/frontend/static/css/pages/game/layout.css")


def test_chat_template_uses_canonical_channel_keys() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert 'data-channel="global"' in template
    assert 'data-channel="zone"' in template
    assert 'chatTab = \'global\'' in template
    assert 'chatTab = \'zone\'' in template
    assert 'channels.global' in template
    assert 'channels.zone' in template
    assert 'hx-trigger="chat-send"' in template
    assert "_sendChat($el.form)" in template
    assert "_rosterTitle()" in template
    assert "_rosterHeading()" in template
    assert "_rosterItems()" in template
    assert 'data-channel="world"' not in template
    assert 'data-channel="local"' not in template


def test_chat_shell_is_floating_overlay() -> None:
    css = CHAT_LAYOUT_CSS.read_text(encoding="utf-8")

    assert "#game-chat-shell" in css
    assert "position: fixed;" in css
    assert "pointer-events: none;" in css
    assert "width: min(100%, 1040px);" in css
    assert "pointer-events: auto;" in css
