from pathlib import Path

CHAT_TEMPLATE = Path("src/frontend/templates/shared/chat/main.html")
CHAT_FOOTER_TEMPLATE = Path("src/frontend/templates/game/includes/chat_footer.html")
CHAT_OVERLAY_TEMPLATE = Path("src/frontend/templates/game/includes/chat_overlay.html")
CHAT_CSS_DIR = Path("src/frontend/static/css/game/domains/chat")
SESSION_CONTENT_TEMPLATE = Path("src/frontend/templates/game/session_content.html")
COMBAT_VIEWPORT_TEMPLATE = Path("src/frontend/templates/game/domains/combat/viewport/main.html")
GAME_MAIN_JS = Path("src/frontend/static/js/core/main.js")
GAME_CATALOG_JS = Path("src/frontend/static/js/core/catalog.js")
TOOLTIPS_CSS = Path("src/frontend/static/css/game/components/tooltips.css")


def read_chat_css() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            CHAT_CSS_DIR / "shell.css",
            CHAT_CSS_DIR / "themes.css",
            CHAT_CSS_DIR / "panel.css",
            CHAT_CSS_DIR / "tabs.css",
            CHAT_CSS_DIR / "messages.css",
            CHAT_CSS_DIR / "input.css",
            CHAT_CSS_DIR / "responsive_states.css",
        )
    )


def test_chat_template_uses_canonical_channel_keys() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert 'data-channel="global"' in template
    assert 'data-channel="zone"' in template
    assert "_activateTab('global')" in template
    assert "_activateTab('zone')" in template
    assert "unreadTabs" in template
    assert "_visibleMessagesForTab('global')" in template
    assert "_visibleMessagesForTab('zone')" in template
    assert 'hx-trigger="chat-send"' in template
    assert "_sendChat($el.form)" in template
    assert "_rosterTitle()" in template
    assert "_rosterHeading()" in template
    assert "_rosterItems()" in template
    assert 'data-channel="world"' not in template
    assert 'data-channel="local"' not in template


def test_chat_template_keeps_combat_logs_in_system_channel() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_isCombatLog(m)" in template
    assert "_ensureCombatTabFromLog" not in template
    assert "_ensureInitialCombatTab" not in template
    assert "combatLogKey" not in template
    assert "channels.dynamic[combatLogKey]" not in template
    assert "_isClosedDynamicTab(key)" in template
    assert "_rememberClosedDynamicTab(key)" in template
    assert "_forgetClosedDynamicTab(dynamicKey)" in template


def test_chat_template_does_not_rebuild_system_messages_during_render() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_systemMessages()" not in template
    assert "slice().reverse()" not in template
    assert 'x-for="(m, idx) in _visibleMessagesForTab(\'system\')"' in template
    assert "_showCombatLogSeparator(_visibleMessagesForTab('system'), idx)" in template


def test_chat_template_can_hide_visible_tab_messages_without_deleting_history() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_hiddenStorageKey(key)" in template
    assert "_clearActiveChatTab()" in template
    assert "_writeHidden(key, this._messageCursor(messages[messages.length - 1]))" in template
    assert "_visibleMessagesForTab('global')" in template
    assert "_visibleMessagesForTab(key)" in template
    assert "CLR" in template


def test_chat_log_is_selectable_not_draggable() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert 'class="chat-log" id="chat-log"' in template
    assert "startDrag" not in template
    assert "doDrag" not in template
    assert "cursor: grab" not in template
    assert "userSelect='none'" not in template


def test_chat_template_renders_combat_logs_from_templates_and_structured_facts() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "x-html" not in template
    assert "_messageHtml(m)" not in template
    assert "_normalizeMessage(raw)" in template
    assert "_buildCombatLogView(msg)" in template
    assert "_templateTextsFrom(value)" in template
    assert "add(item.parts)" in template
    assert "add(item.texts)" in template
    assert "add(item.fragments)" in template
    assert "...this._templateTextsFrom(m.templates)" in template
    assert "join(', ')" in template
    assert "_combatLogParts(msg)" in template
    assert "_combatFactItems(msg)" in template
    assert "_messageParts(m)" in template
    assert "_messageIcon(m)" in template
    assert "_combatLogIconUrl(msg)" in template
    assert "chat-message-icon" in template
    assert "_messageFacts(m)" in template
    assert "_messagePartClass(part)" in template
    assert "_messageFactClass(fact)" in template
    assert "_actorTemplateValues(variables)" in template
    assert "_pushRenderedTextParts(parts, msg.content, variables)" in template
    assert "actors.sort((a, b) => b.text.length - a.text.length)" in template
    assert "combat-log-var--source" in template
    assert "combat-log-var--target" in template
    assert "token-' + token + '.svg'" in template
    assert "(result.triggers || [])" in template


def test_chat_template_resolves_combat_log_text_from_combat_text_catalog() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_combatTextTemplate(msg)" in template
    assert "cache.getCombatTextTemplate(template.key)" in template
    assert "cache.renderCombatText(template.key, msg.variables || {})" in template
    assert "_combatLogParts(msg)" in template
    assert "_templateTexts(msg)" in template
    assert "_templateTextsFrom(m.template)" not in template


def test_chat_template_resolves_combat_token_facts_from_catalog() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_catalogEntry('combat_tokens', token)" in template
    assert "_catalogField(entry, 'title')" in template
    assert "_catalogField(entry, 'description')" in template
    assert "_tokenFactItem(item)" in template
    assert "const tooltipHead = title ? [title, amount].filter(Boolean).join('. ') : (amount || text)" in template
    assert "const tooltip = [tooltipHead, description].filter(Boolean).join('. ')" in template
    assert "catalog: token ? 'combat_tokens' : ''" in template
    assert "catalogKey: token" in template
    assert "data-tippy-content" in template
    assert "GameCatalogCache.init().then(() => { _refreshMessageViews(); })" in template


def test_chat_combat_fact_tooltips_do_not_use_native_browser_titles() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")
    main_js = GAME_MAIN_JS.read_text(encoding="utf-8")
    catalog_js = GAME_CATALOG_JS.read_text(encoding="utf-8")

    assert ':title="_messageText(' not in template
    assert ':title="fact.tooltip || fact.text"' not in template
    assert 'data-tippy-theme="game-hint"' in template
    assert "node.removeAttribute('title')" in main_js
    assert "node.removeAttribute('title')" in catalog_js


def test_chat_template_resource_facts_include_delta_before_current_value() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "const delta = resource.delta" in template
    assert "const deltaText = this._signedAmount(delta)" in template
    assert "`${deltaText} ${kind} -> ${value}`" in template


def test_game_tooltips_preserve_line_breaks_without_html() -> None:
    main_js = GAME_MAIN_JS.read_text(encoding="utf-8")
    catalog_js = GAME_CATALOG_JS.read_text(encoding="utf-8")
    css = TOOLTIPS_CSS.read_text(encoding="utf-8")

    for source in (main_js, catalog_js):
        assert "replace(/\\\\n/g, '\\n')" in source
        assert "replace(/\\s+\\/\\/\\s+/g, '\\n')" in source
        assert "allowHTML: false" in source
        assert "content(reference)" in source

    assert "white-space: pre-line;" in css


def test_session_content_does_not_render_footer_chat_shell() -> None:
    template = SESSION_CONTENT_TEMPLATE.read_text(encoding="utf-8")

    assert 'id="game-chat-shell"' not in template
    assert 'id="game-footer-shell" hx-swap-oob="outerHTML"' in template
    assert 'include "game/includes/chat_footer.html"' not in template
    assert 'include "game/includes/chat_overlay.html"' in template


def test_combat_refresh_selects_only_main_content_shell() -> None:
    template = COMBAT_VIEWPORT_TEMPLATE.read_text(encoding="utf-8")

    assert 'hx-select="#main-content > .shell-constrained"' in template
    assert 'hx-select=".shell-constrained"' not in template


def test_chat_css_has_rich_combat_log_styles() -> None:
    css = read_chat_css()

    assert ".combat-log-var--source" in css
    assert ".combat-log-var--target" in css
    assert ".chat-message-icon" in css
    assert ".combat-fact--token" in css
    assert ".combat-fact--effect" in css


def test_chat_shell_is_collapsible_footer() -> None:
    css = read_chat_css()
    index = CHAT_CSS_DIR.joinpath("index.css").read_text(encoding="utf-8")
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")
    footer = CHAT_FOOTER_TEMPLATE.read_text(encoding="utf-8")
    overlay = CHAT_OVERLAY_TEMPLATE.read_text(encoding="utf-8")
    base = Path("src/frontend/templates/game/base_game.html").read_text(encoding="utf-8")
    header = Path("src/frontend/templates/game/includes/header.html").read_text(encoding="utf-8")
    shell_js = Path("src/frontend/static/js/core/game_shell.js").read_text(encoding="utf-8")
    main_js = GAME_MAIN_JS.read_text(encoding="utf-8")

    assert ".game-chat-footer" in css
    assert ".game-chat-footer-shell" in css
    assert "flex: 1 1 auto;" in css
    assert "width: 100%;" in css
    assert ".game-chat-footer .game-chat-row" in css
    assert ".game-chat-footer .chat-step-0" in css
    assert ".game-chat-footer .chat-step-0 .chat-tabs" in css
    assert "display: flex !important;" in css
    assert ".game-chat-footer .chat-step-0 .chat-main-area" in css
    assert ".game-chat-footer .chat-step-0 #chat-input-form" in css
    assert "bottom: 0;" in css
    assert "--game-chat-width: 1440px;" in css
    assert "width: min(100%, var(--game-chat-width));" in css
    assert ".chat-tab-select-wrap" in css
    assert ".chat-tab-select" in css
    assert "@media (max-width: 767px)" in css
    assert '@import url("shell.css");' in index
    assert '@import url("responsive_states.css");' in index
    assert "#game-chat-shell" not in css
    assert "game-chat-footer-bar" not in footer
    assert "game-chat-footer-tabs" not in footer
    assert "game-chat-footer-mobile" not in footer
    assert "game-chat-footer-toggle" not in footer
    assert 'include "shared/chat/main.html"' not in footer
    assert 'include "game/includes/chat_footer.html"' not in base
    assert 'include "game/includes/chat_overlay.html"' in base
    assert 'include "shared/chat/main.html"' in overlay
    assert "game-chat-toggle" in header
    assert 'aria-controls="game-chat-container"' in header
    assert "is-chat-closed" not in footer
    assert "setChatStep(1)" not in footer
    assert "setChatStep(0)" in template
    assert 'class="chat-win-controls" @click.stop' in template
    assert "chat-tab-select-wrap" in template
    assert "chat-tab-select" in template
    assert "_tabSelectLabel(key)" in template
    assert "@change=\"_activateTab($event.target.value)\"" in template
    assert "data-chat-minmax-label" in template
    assert "toggleChatMinMax()" in template
    assert "chatMinimized ? '100px'" not in base
    assert "getPropertyValue('--game-footer-height')" in main_js
    assert "chatRow.classList.remove('chat-step-0'" in main_js
    assert "chatRow.style.removeProperty('height')" in main_js
    assert "data-chat-minmax-label" in main_js
    assert "window.toggleChatMinMax" in main_js
    assert "chatStep: 0" in shell_js
    assert "chatStep: Alpine.$persist" not in shell_js
    assert "chatHeight: Alpine.$persist" not in shell_js
    assert 'class="chat-users"' not in template
