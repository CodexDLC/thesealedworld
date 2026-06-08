from pathlib import Path

CHAT_TEMPLATE = Path("src/frontend/templates/shared/chat/main.html")
CHAT_FOOTER_TEMPLATE = Path("src/frontend/templates/game/includes/chat_footer.html")
CHAT_OVERLAY_TEMPLATE = Path("src/frontend/templates/game/includes/chat_overlay.html")
CHAT_CSS_DIR = Path("src/frontend/static/css/game/domains/chat")
SESSION_CONTENT_TEMPLATE = Path("src/frontend/templates/game/session_content.html")
COMBAT_VIEWPORT_TEMPLATE = Path("src/frontend/templates/game/domains/combat/viewport/main.html")
GAME_MAIN_JS = Path("src/frontend/static/js/core/main.js")
GAME_REALTIME_SUPERVISOR_JS = Path("src/frontend/static/js/core/realtime_supervisor.js")
HTMX_WS_JS = Path("src/frontend/static/js/vendor/htmx-ws.js")
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


def test_chat_template_uses_realtime_ws_endpoint() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert 'ws-connect="{{ realtime_ws_endpoint }}' in template
    assert "chat_ws_endpoint" not in template
    assert "/ws/chat" not in template


def test_chat_template_silences_transport_ping_envelope() -> None:
    """``ping`` is handled by static/js/core/realtime_supervisor.js — the chat
    shell must drop it without logging, otherwise every heartbeat (~20s) spams
    'realtime: ignoring envelope type ping' into the console.
    """
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "envelope.type === 'ping'" in template
    # The ping branch must short-circuit BEFORE the generic ignore-warn so the
    # supervisor's heartbeat never reaches the console fallback.
    ping_idx = template.index("envelope.type === 'ping'")
    warn_idx = template.index("ignoring envelope type")
    assert ping_idx < warn_idx


def test_realtime_supervisor_only_nudges_stale_sockets_with_reconnect_code() -> None:
    source = GAME_REALTIME_SUPERVISOR_JS.read_text(encoding="utf-8")

    assert "const HTMX_RECONNECT_CODE = 1012;" in source
    assert "const STALE_CONNECTING_MS = 10000;" in source
    assert "const STALE_OPEN_MS = 45000;" in source
    assert "event.target || event.currentTarget || null" in source
    assert "currentSocket.close(HTMX_RECONNECT_CODE, 'stale realtime socket')" in source
    assert "state === 0 && ageMs >= STALE_CONNECTING_MS" in source
    assert "state === 1 && idleMs >= STALE_OPEN_MS" in source
    assert "if (state === 0 || state === 1)" not in source


def test_realtime_supervisor_replies_to_ping_via_htmx_ws_public_interface() -> None:
    source = GAME_REALTIME_SUPERVISOR_JS.read_text(encoding="utf-8")

    assert "typeof socketWrapper.sendImmediately !== 'function'" in source
    assert "socketWrapper.sendImmediately(JSON.stringify({ type: 'pong' }))" in source
    assert "socketWrapper.socket" not in source


def test_realtime_supervisor_reconnects_after_auth_keepalive() -> None:
    source = GAME_REALTIME_SUPERVISOR_JS.read_text(encoding="utf-8")
    htmx_ws = HTMX_WS_JS.read_text(encoding="utf-8")

    assert "reconnect: wrapper.init.bind(wrapper)" in htmx_ws
    assert "function reconnectSocket(detail)" in source
    assert "typeof socketWrapper.reconnect !== 'function'" in source
    assert "socketWrapper.reconnect()" in source
    assert "consumeKeepalive().then((ok) => {" in source
    assert "reconnectSocket(detail);" in source


def test_chat_template_never_embeds_access_token_in_ws_url() -> None:
    """Auth comes from the cookie; the token MUST NOT be in the URL.

    Embedding {{ access_token }} freezes a 15-min credential into the DOM and
    htmx-ws will retry the same dead URL forever once it expires. See
    src/backend/realtime/api/ws.py for the cookie-based handshake.
    """
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    # The whole ws-connect line must not carry a token query parameter.
    for line in template.splitlines():
        if "ws-connect=" not in line:
            continue
        assert "token=" not in line, f"WS URL must not carry a token query: {line!r}"
        assert "{{ access_token" not in line
        assert "{{ game_access_token" not in line


def test_chat_template_sends_typed_envelopes_and_unwraps_chat_message() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    # outgoing envelope shape
    assert "type: 'chat.send'" in template
    # inbound envelope handling
    assert "envelope.type" in template
    assert "'chat.message'" in template
    assert "envelope.payload" in template
    assert "_messageText(m)" in template
    assert 'x-show="!_isCombatLog(m)" x-text="_messageText(m)"' in template
    assert 'x-show="_isCombatLog(m)"' in template
    assert "system.session_replaced" in template
    # ws-connect must be the realtime endpoint, used exactly once
    assert template.count("ws-connect=") == 1


def test_chat_template_renders_player_notice_into_system_tab() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    # _onWsMessage routes player.notice to a dedicated handler before the
    # chat.message rejection branch.
    assert "envelope.type === 'player.notice'" in template
    assert "this._onPlayerNotice(envelope)" in template
    # notice templates are frontend-owned and filled via the existing renderer
    assert "_noticeTemplates" in template
    assert "_renderNoticeText(key, vars)" in template
    assert "this._renderTemplateText(template, vars || {})" in template
    # a few of the classic-MMO notice strings + placeholder usage
    assert "'player.death': 'Вы погибли.'" in template
    assert "'combat.started': 'На часах {time}. Из засады начался бой: {participants}.'" in template
    assert "'combat.finished': 'На часах {time}. Бой завершен: {outcome}. Участники: {participants}.'" in template
    assert "'loot.items_claimed': 'Вы подобрали: {summary}.'" in template
    assert "'exploration.safe_zone_entered': 'Вы вошли в безопасную зону: {location}.'" in template
    # the synthesized message lands in the system channel as a plain message
    assert "_onPlayerNotice(envelope)" in template
    assert "channel: 'system'" in template
    assert "this.channels.system.push" in template
    assert "presentation !== 'system_chat'" in template


def test_chat_template_refresh_notice_wakes_existing_fragment() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    # refresh presentation is routed before system_chat handling
    assert "presentation === 'refresh'" in template
    assert "this._onRefreshNotice(envelope.payload || {})" in template
    # reuses the existing character-status-refresh HTMX hook (no new visual UI)
    assert "_refreshEvents" in template
    assert "'status': 'character-status-refresh'" in template
    assert "window.htmx.trigger(document.body, eventName)" in template
    # also dispatches a generic opt-in event for other fragments
    assert "new CustomEvent('realtime:refresh'" in template


def test_chat_template_does_not_treat_combat_logs_as_system_channel_history() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_isCombatLog(m)" in template
    assert "_ensureCombatTabFromLog" not in template
    assert "_ensureInitialCombatTab" not in template
    assert "combatLogKey" not in template
    assert "channels.dynamic[combatLogKey]" not in template
    assert "_showCombatLogSeparator(_visibleMessagesForTab('system'), idx)" not in template
    assert "_isClosedDynamicTab(key)" in template
    assert "_rememberClosedDynamicTab(key)" in template
    assert "_forgetClosedDynamicTab(dynamicKey)" in template


def test_chat_template_does_not_rebuild_system_messages_during_render() -> None:
    template = CHAT_TEMPLATE.read_text(encoding="utf-8")

    assert "_systemMessages()" not in template
    assert "slice().reverse()" not in template
    assert 'x-for="(m, idx) in _visibleMessagesForTab(\'system\')"' in template
    assert "_showCombatLogSeparator(_visibleMessagesForTab('system'), idx)" not in template


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
        assert "content(reference)" in source

    assert "allowHTML: false" in main_js
    assert "allowHTML: node.dataset.tippyHtml === '1'" in catalog_js
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
    assert "#chat-input-form" in css
    assert "flex: 0 0 auto;" in css
    assert "min-height: 42px;" in css
    assert "position: relative;" in css
    assert "z-index: 2;" in css
    assert "flex: 1 1 16rem;" in css
    assert "min-width: 12rem;" in css
    assert "caret-color: var(--chat-accent);" in css
    assert "#chat-input::placeholder" in css
    assert "border-color: color-mix(in srgb, var(--chat-accent) 46%, transparent);" in css
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
    # Desktop chat no longer exposes step 0 (the collapsed-strip mode is mobile-only).
    assert "setChatStep(0)" not in template
    assert "setChatStep(1)" in template
    assert 'class="chat-win-controls" @click.stop' in template
    assert "chat-tab-select-wrap" in template
    assert "chat-tab-select-trigger" in template
    assert "chat-tab-select-dropdown" in template
    assert "mobileSelectOpen" in template
    assert "data-chat-minmax-label" in template
    assert "toggleChatMinMax()" in template
    assert "chatMinimized ? '100px'" not in base
    assert "getPropertyValue('--game-footer-height')" in main_js
    assert "chatRow.classList.remove('chat-step-0'" in main_js
    assert "chatRow.style.removeProperty('height')" in main_js
    assert "data-chat-minmax-label" in main_js
    assert "window.toggleChatMinMax" in main_js
    assert "chatStep: chatWindowObj.open ? 2 : 0" in shell_js
    assert "chatStep: Alpine.$persist" not in shell_js
    assert "chatHeight: Alpine.$persist" not in shell_js
    assert 'class="chat-users"' not in template
