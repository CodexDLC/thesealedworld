(function () {
    const loadedScripts = new Set();
    const pendingScripts = new Map();

    function parseScripts(root) {
        if (!root || !root.dataset.gameScripts) {
            return [];
        }

        try {
            const scripts = JSON.parse(root.dataset.gameScripts);
            return Array.isArray(scripts) ? scripts.filter((src) => typeof src === "string" && src) : [];
        } catch (_error) {
            return [];
        }
    }

    function scriptKey(src) {
        try {
            return new URL(src, window.location.href).href;
        } catch (_error) {
            return src;
        }
    }

    function ensureScript(src) {
        const key = scriptKey(src);
        if (loadedScripts.has(key) || document.querySelector(`script[data-game-state-script="${key}"]`)) {
            loadedScripts.add(key);
            return Promise.resolve();
        }
        if (pendingScripts.has(key)) {
            return pendingScripts.get(key);
        }

        const promise = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = key;
            script.defer = true;
            script.dataset.gameStateScript = key;
            script.onload = () => {
                loadedScripts.add(key);
                pendingScripts.delete(key);
                resolve();
            };
            script.onerror = () => {
                pendingScripts.delete(key);
                reject(new Error(`GAME_STATE_SCRIPT_FAILED: ${key}`));
            };
            document.head.append(script);
        });
        pendingScripts.set(key, promise);
        return promise;
    }

    function rootsFromScope(scope) {
        const root = scope instanceof Element ? scope : document;
        const roots = [];
        if (root instanceof Element && root.matches("[data-game-state]")) {
            roots.push(root);
        }
        root.querySelectorAll("[data-game-state]").forEach((item) => roots.push(item));
        return roots;
    }

    function initRoot(root) {
        const state = root.dataset.gameState || "";
        const scripts = parseScripts(root);
        return Promise.all(scripts.map(ensureScript))
            .then(() => {
                const registry = window.GameStates || {};
                const handler = registry[state];
                if (handler && typeof handler.init === "function") {
                    handler.init(root);
                }
            })
            .catch((error) => {
                console.error(error);
            });
    }

    function init(scope) {
        return Promise.all(rootsFromScope(scope || document).map(initRoot));
    }

    window.GameStates = window.GameStates || {};
    window.GameStateLoader = {
        init,
        ensureScript,
    };

    document.addEventListener("DOMContentLoaded", () => init(document));
    document.addEventListener("htmx:load", (event) => init(event.target));
    document.addEventListener("htmx:afterSwap", (event) => init(event.target));
})();
