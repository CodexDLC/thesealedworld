// Realtime WebSocket reconnect supervisor.
//
// The chat shell wires htmx-ws to /ws/realtime with auth coming from the
// HttpOnly cookie (see src/backend/realtime/api/ws.py). htmx-ws keeps the
// transport itself alive but doesn't know what to do when the handshake is
// rejected with an auth-class close code — it will retry the same URL
// forever. This supervisor watches close/error events and breaks the loop:
//
//   * Auth-class close (4001/4003/4004): one keepalive call to /game/keepalive
//     so GameTokenRefreshMiddleware rotates the cookie before htmx-ws retries.
//     After 3 consecutive failures we redirect to the lobby — the refresh
//     token itself is gone.
//   * Session replaced (4002): redirect immediately, the other tab won.
//   * Heartbeat timeout (4008): treat as a generic transport drop, let
//     htmx-ws reconnect normally.
//   * Pong: respond to backend pings so the server-side liveness loop
//     keeps the socket open across NAT idle timeouts.

(function () {
    const AUTH_CODES = new Set([4001, 4003, 4004]);
    const SESSION_REPLACED_CODE = 4002;
    const MAX_AUTH_RETRIES = 3;
    const HTMX_RECONNECT_CODE = 1012;
    // Server does accept() then close(4001) so wsOpen fires every reject.
    // Reset the counter only when the socket is alive long enough to either
    // receive a message or stay open beyond this threshold; otherwise an
    // accept-then-close storm would never trip the retry cap.
    const LIVENESS_RESET_MS = 5000;
    const STALE_CONNECTING_MS = 10000;
    const STALE_OPEN_MS = 45000;
    const KEEPALIVE_URL = '/game/keepalive';
    const LOBBY_URL = '/game-lobby?reason=session_lost';

    let authFailures = 0;
    let keepalivePending = null;
    let openedAt = 0;
    let lastActivityAt = 0;
    let livenessResetTimer = null;
    let currentSocket = null;

    function consumeKeepalive() {
        if (keepalivePending) return keepalivePending;
        keepalivePending = fetch(KEEPALIVE_URL, {
            method: 'GET',
            credentials: 'include',
            cache: 'no-store',
            headers: { 'X-Requested-With': 'realtime-supervisor' },
        }).then((r) => r.ok).catch(() => false).finally(() => {
            keepalivePending = null;
        });
        return keepalivePending;
    }

    function bailToLobby() {
        if (window.location.pathname.startsWith('/game-lobby')) return;
        window.location.replace(LOBBY_URL);
    }

    function clearLivenessTimer() {
        if (livenessResetTimer) {
            clearTimeout(livenessResetTimer);
            livenessResetTimer = null;
        }
    }

    function reconnectSocket(detail) {
        const socketWrapper = detail && detail.socketWrapper;
        if (!socketWrapper || typeof socketWrapper.reconnect !== 'function') return;
        try {
            socketWrapper.reconnect();
        } catch (_) {
            // If reconnect itself fails, the next page-level navigation will
            // create a fresh htmx-ws instance.
        }
    }

    function onWsClose(detail) {
        clearLivenessTimer();
        currentSocket = null;
        const code = detail && detail.event ? detail.event.code : null;
        if (code === SESSION_REPLACED_CODE) {
            bailToLobby();
            return;
        }
        if (AUTH_CODES.has(code)) {
            authFailures += 1;
            if (authFailures > MAX_AUTH_RETRIES) {
                bailToLobby();
                return;
            }
            consumeKeepalive().then((ok) => {
                // Keepalive returned non-2xx -> backend refused to refresh.
                // The session is gone (either the refresh cookie expired or
                // another tab claimed the slot); no point retrying further.
                if (!ok) {
                    bailToLobby();
                    return;
                }
                reconnectSocket(detail);
            });
            return;
        }
        // Non-auth close: if the socket was actually alive for a while, reset
        // the counter so a single network blip doesn't bank toward a future
        // auth-class redirect. If it died instantly, leave the counter alone.
        if (openedAt && Date.now() - openedAt >= LIVENESS_RESET_MS) {
            authFailures = 0;
        }
    }

    function onWsOpen(evt) {
        openedAt = Date.now();
        lastActivityAt = openedAt;
        const event = evt && evt.detail ? evt.detail.event : null;
        currentSocket = event ? (event.target || event.currentTarget || null) : null;
        clearLivenessTimer();
        // If the socket stays open for LIVENESS_RESET_MS without an immediate
        // close, treat it as a healthy session and forget past auth failures.
        livenessResetTimer = setTimeout(() => {
            authFailures = 0;
            livenessResetTimer = null;
        }, LIVENESS_RESET_MS);
    }

    // Force htmx-ws to drop a half-dead socket so its built-in reconnect loop
    // picks up immediately. Useful when the OS/browser froze the tab and the
    // server already closed us out via heartbeat, but the client-side socket
    // is stuck in CONNECTING/OPEN without ever firing wsClose.
    function nudgeReconnectIfStale() {
        if (!currentSocket) return;
        const state = currentSocket.readyState;
        const ageMs = Date.now() - openedAt;
        const idleMs = Date.now() - (lastActivityAt || openedAt);
        // CLOSED (3) or CLOSING (2): htmx-ws is already reconnecting; nothing to do.
        // CONNECTING (0) for too long, or OPEN (1) with no server traffic past
        // the heartbeat interval — force close with a code htmx-ws reconnects on.
        if ((state === 0 && ageMs >= STALE_CONNECTING_MS) || (state === 1 && idleMs >= STALE_OPEN_MS)) {
            try {
                currentSocket.close(HTMX_RECONNECT_CODE, 'stale realtime socket');
            } catch (_) {
                // Swallow — htmx-ws will try a fresh socket on the next tick.
            }
        }
    }

    function onVisibilityChange() {
        if (document.visibilityState === 'visible') {
            nudgeReconnectIfStale();
        }
    }

    function onNetworkOnline() {
        nudgeReconnectIfStale();
    }

    function onWsAfterMessage(evt) {
        const message = evt && evt.detail ? evt.detail.message : null;
        if (!message) return;
        lastActivityAt = Date.now();
        // Any inbound payload is proof of a healthy session — drop the
        // failure counter immediately (the LIVENESS_RESET_MS timer was a
        // fallback for sockets that never speak).
        authFailures = 0;
        clearLivenessTimer();
        let parsed;
        try {
            parsed = JSON.parse(message);
        } catch (_) {
            return;
        }
        if (!parsed || parsed.type !== 'ping') return;
        const socketWrapper = evt.detail.socketWrapper;
        if (!socketWrapper || typeof socketWrapper.sendImmediately !== 'function') return;
        try {
            socketWrapper.sendImmediately(JSON.stringify({ type: 'pong' }));
        } catch (_) {
            // Socket already dying; close handler will pick it up.
        }
    }

    document.addEventListener('htmx:wsOpen', onWsOpen);
    document.addEventListener('htmx:wsClose', (e) => onWsClose(e && e.detail));
    document.addEventListener('htmx:wsError', (e) => onWsClose(e && e.detail));
    document.addEventListener('htmx:wsAfterMessage', onWsAfterMessage);
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('online', onNetworkOnline);

    window.RealtimeSupervisor = {
        // Exposed for diagnostics / tests.
        _state: () => ({
            authFailures,
            keepalivePending: !!keepalivePending,
            openedAt,
            lastActivityAt,
        }),
        _reset: () => {
            authFailures = 0;
            keepalivePending = null;
            openedAt = 0;
            lastActivityAt = 0;
            currentSocket = null;
            clearLivenessTimer();
        },
        _nudge: nudgeReconnectIfStale,
    };
})();
