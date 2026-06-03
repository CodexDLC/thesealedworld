window.inventoryGridLayout = function(element) {
    if (!element) return null;

    const root = element.closest(".inventory-shell") || element;
    const frame = element.closest(".right-inventory-panel") || root;
    const readNumber = (value, fallback) => {
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    };

    const update = () => {
        const styles = window.getComputedStyle(root);
        const gap = readNumber(styles.getPropertyValue("--inventory-grid-gap"), 5);
        const baseCell = readNumber(styles.getPropertyValue("--inventory-grid-base-cell"), 34);
        const cols = Math.max(1, Math.round(readNumber(styles.getPropertyValue("--inventory-grid-cols"), 12)));
        const extraRows = Math.max(0, Math.round(readNumber(styles.getPropertyValue("--inventory-grid-extra-rows"), 2)));
        const width = Math.max(0, frame.clientWidth - 48);
        if (width <= 0) return;

        const cell = Math.max(22, Math.min(baseCell, (width - gap * (cols - 1)) / cols));
        const capacity = Math.max(1, Math.ceil(readNumber(element.dataset.inventoryCells, cols * 5)));
        const rows = Math.max(1, Math.ceil(capacity / cols) + extraRows);
        const framePadding = 16;
        const gridWidth = cols * cell + gap * Math.max(0, cols - 1) + framePadding;
        const gridHeight = rows * cell + gap * Math.max(0, rows - 1);
        const viewportHeight = Math.min(gridHeight, Math.max(cell * 5, frame.clientHeight * 0.42));
        root.style.setProperty("--inventory-cell", `${cell}px`);
        root.style.setProperty("--inventory-grid-rows", String(rows));
        root.style.setProperty("--inventory-grid-width", `${gridWidth}px`);
        root.style.setProperty("--inventory-grid-height", `${gridHeight}px`);
        root.style.setProperty("--inventory-grid-viewport-height", `${viewportHeight}px`);
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(frame);
    window.addEventListener("resize", update, { passive: true });
    return () => {
        observer.disconnect();
        window.removeEventListener("resize", update);
    };
};

window.gameShell = function(initial = {}) {
    const activeCharId = initial.activeCharId || "";
    const domain = initial.domain || "";
    const parseCssPx = (value, fallback) => {
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    };
    const shellMetrics = () => {
        const root = document.getElementById("app-viewport") || document.documentElement;
        const styles = window.getComputedStyle(root);
        const header = parseCssPx(styles.getPropertyValue("--game-header-height"), 40);
        const footer = parseCssPx(styles.getPropertyValue("--game-footer-height"), 24);
        const inset = window.matchMedia("(max-width: 768px)").matches ? 6 : 8;
        return {
            header,
            footer,
            inset,
            top: header + inset,
            bottom: footer + inset,
            isMobile: window.matchMedia("(max-width: 768px)").matches,
        };
    };
    const hudStorageKey = (name) => `tbmmorpg:hud:${name}:geometry:v1`;
    const hudOpenStorageKey = (name) => {
        const scope = activeCharId || "global";
        return `tbmmorpg:hud:${name}:open:${scope}:v1`;
    };
    const panelStateStorageKey = () => {
        const scope = activeCharId || "global";
        const domainScope = domain || "global";
        const viewportScope = isDrawerViewport() ? "drawer" : "desktop";
        return `tbmmorpg:shell:panels:${domainScope}:${scope}:${viewportScope}:v1`;
    };
    const isDrawerViewport = () => window.matchMedia("(max-width: 1024px)").matches;
    const clearDrawerPanelState = () => {
        try {
            window.localStorage.removeItem(panelStateStorageKey());
        } catch (_error) {
            return;
        }
    };
    const worldDesktopPanelsDefaultOpen = () => {
        if (!["exploration", "rift"].includes(domain)) return false;
        return window.matchMedia("(min-width: 1025px)").matches;
    };
    const unavailableModalCopy = {
        quests: {
            eyebrow: "QUEST SYSTEM",
            title: "Система квестов будет доступна позже",
            body: "Этот раздел сейчас в разработке. Когда он будет готов, здесь появятся активные задачи, следы, цепочки событий и журнал решений.",
        },
    };
    const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
    })[char]);
    const noInventoryDomains = ["combats", "death", "loot"];
    const defaultRightPanelView = domain === "combats" ? "enemies" : "context";
    const normalizeLeftPanelView = (value) => {
        const view = typeof value === "string" ? value : "status";
        if (domain === "combats" && !["status", "allies"].includes(view)) {
            return "status";
        }
        return view;
    };
    const normalizeRightPanelView = (value) => {
        const view = typeof value === "string" ? value : defaultRightPanelView;
        if (domain === "combats" && !["enemies", "log"].includes(view)) {
            return "enemies";
        }
        if (noInventoryDomains.includes(domain) && view === "inventory") {
            return defaultRightPanelView;
        }
        return view;
    };
    const loadPanelState = () => {
        if (isDrawerViewport()) {
            clearDrawerPanelState();
            return null;
        }
        try {
            const raw = window.localStorage.getItem(panelStateStorageKey());
            if (!raw) return null;
            const saved = JSON.parse(raw);
            if (typeof saved?.leftOpen !== "boolean" || typeof saved?.rightOpen !== "boolean") return null;
            return {
                leftOpen: saved.leftOpen,
                rightOpen: saved.rightOpen,
                leftPanelView: normalizeLeftPanelView(saved.leftPanelView),
                rightPanelView: normalizeRightPanelView(saved.rightPanelView),
            };
        } catch (_error) {
            window.localStorage.removeItem(panelStateStorageKey());
            return null;
        }
    };
    const savePanelState = (state) => {
        if (isDrawerViewport()) {
            clearDrawerPanelState();
            return;
        }
        try {
            window.localStorage.setItem(panelStateStorageKey(), JSON.stringify({
                leftOpen: Boolean(state.leftOpen),
                rightOpen: Boolean(state.rightOpen),
                leftPanelView: normalizeLeftPanelView(state.leftPanelView),
                rightPanelView: normalizeRightPanelView(state.rightPanelView),
            }));
        } catch (_error) {
            return;
        }
    };
    const saveHudOpenState = (name, isOpen) => {
        try {
            window.localStorage.setItem(hudOpenStorageKey(name), JSON.stringify({ open: Boolean(isOpen) }));
        } catch (_error) {
            return;
        }
    };
    const saveHudGeometry = (name, hudWindow) => {
        if (hudWindow.x === null || hudWindow.y === null || hudWindow.width === null || hudWindow.height === null) {
            return;
        }
        window.localStorage.setItem(hudStorageKey(name), JSON.stringify({
            x: Math.round(hudWindow.x),
            y: Math.round(hudWindow.y),
            width: Math.round(hudWindow.width),
            height: Math.round(hudWindow.height),
        }));
    };
    const loadHudWindow = (name, defaults = {}) => {
        let geometry = { dragging: false, resizing: false, resizeEdge: "", open: false };
        try {
            const rawGeo = window.localStorage.getItem(hudStorageKey(name));
            if (rawGeo) {
                const parsed = JSON.parse(rawGeo);
                if (parsed.x !== undefined) geometry.x = parsed.x;
                if (parsed.y !== undefined) geometry.y = parsed.y;
                if (parsed.width !== undefined) geometry.width = parsed.width;
                if (parsed.height !== undefined) geometry.height = parsed.height;
            }
            const rawOpen = window.localStorage.getItem(hudOpenStorageKey(name));
            if (rawOpen) {
                geometry.open = JSON.parse(rawOpen).open;
            } else if (defaults.open !== undefined) {
                geometry.open = defaults.open;
            }
        } catch (_e) {}
        return Object.assign({}, defaults, geometry);
    };

    const savedPanelState = loadPanelState();
    const defaultPanelsOpen = worldDesktopPanelsDefaultOpen();
    const initialPanelState = savedPanelState || {
        leftOpen: !isDrawerViewport() && defaultPanelsOpen,
        rightOpen: !isDrawerViewport() && defaultPanelsOpen,
        leftPanelView: "status",
        rightPanelView: defaultRightPanelView,
    };
    const chatLauncher = {
        x: null,
        y: null,
        dragging: false,
        dragMoved: false,
        dragOffsetX: 0,
        dragOffsetY: 0,
        startX: 0,
        startY: 0,
    };

    const chatWindowObj = loadHudWindow("chat", {
        open: false,
        width: 920,
        height: 540,
        x: Math.round((window.innerWidth - 920) / 2),
        y: Math.round((window.innerHeight - 540) / 2)
    });

    return {
        chatTab: "global",
        chatHeight: chatWindowObj.open ? chatWindowObj.height : 30,
        chatMinimized: !chatWindowObj.open,
        chatStep: chatWindowObj.open ? 2 : 0,
        chatClosed: !chatWindowObj.open,
        chatUnread: false,
        selectedAgentId: activeCharId,
        domain,
        agents: {
            [activeCharId]: initial.initialStatus || {},
        },
        leftPanelView: initialPanelState.leftPanelView,
        rightPanelView: initialPanelState.rightPanelView,
        panelStateUserEdited: savedPanelState !== null,
        windows: {
            chat: chatWindowObj
        },
        chatLauncher,
        leftOpen: initialPanelState.leftOpen,
        rightOpen: initialPanelState.rightOpen,

        togglePanel(detail = {}) {
            if (detail.side === "left") {
                const nextView = detail.view || this.leftPanelView;
                if (!detail.forceOpen && this.leftOpen && this.leftPanelView === nextView) {
                    this.leftOpen = false;
                    this.panelStateUserEdited = true;
                    savePanelState(this);
                    return;
                }
                if (detail.view) this.leftPanelView = detail.view;
                this.leftOpen = true;
                this.panelStateUserEdited = true;
                savePanelState(this);
            }
            if (detail.side === "right") {
                const nextView = detail.view || this.rightPanelView;
                if (!detail.forceOpen && this.rightOpen && this.rightPanelView === nextView) {
                    this.rightOpen = false;
                    this.panelStateUserEdited = true;
                    savePanelState(this);
                    return;
                }
                if (detail.view) this.rightPanelView = detail.view;
                this.rightOpen = true;
                this.panelStateUserEdited = true;
                savePanelState(this);
            }
        },

        openChatOverlay() {
            this.chatClosed = false;
            this.chatUnread = false;
            if (this.windows.chat) {
                this.windows.chat.open = true;
                saveHudOpenState('chat', true);
            }
            if (typeof window.setChatStep === "function") {
                window.setChatStep(2);
                return;
            }
            this.chatStep = 2;
            this.chatMinimized = false;
        },

        closeChatOverlay() {
            this.chatClosed = true;
            if (this.windows.chat) {
                this.windows.chat.open = false;
                saveHudOpenState('chat', false);
            }
            if (typeof window.setChatStep === "function") {
                window.setChatStep(0);
                return;
            }
            this.chatStep = 0;
            this.chatMinimized = true;
        },

        toggleChatOverlay() {
            if (this.chatClosed) {
                this.openChatOverlay();
            } else {
                this.closeChatOverlay();
            }
        },

        toggleHudWindow(name) {
            if (name === 'chat') {
                this.toggleChatOverlay();
                return;
            }
            const hudWindow = this.windows[name];
            if (!hudWindow) return;
            hudWindow.open = !hudWindow.open;
            saveHudOpenState(name, hudWindow.open);
        },

        openUnavailableModal(detail = {}) {
            const modalRoot = document.getElementById("game-modal-root");
            if (!modalRoot) return;

            const copy = Object.assign({}, unavailableModalCopy[detail.kind] || {
                eyebrow: "SYSTEM",
                title: "Система будет доступна позже",
                body: "Этот функционал сейчас находится в разработке.",
            });
            if (detail.eyebrow) copy.eyebrow = detail.eyebrow;
            if (detail.title) copy.title = detail.title;
            if (detail.body) copy.body = detail.body;
            modalRoot.innerHTML = `
                <div class="game-modal-backdrop" role="presentation" onclick="if (event.target === this) this.closest('#game-modal-root').innerHTML = ''">
                    <section class="game-unavailable-modal" role="dialog" aria-modal="true" aria-labelledby="game-unavailable-modal-title">
                        <header class="game-unavailable-modal__head">
                            <span>${escapeHtml(copy.eyebrow)}</span>
                            <button class="game-modal-close" type="button" aria-label="Close modal" onclick="this.closest('#game-modal-root').innerHTML = ''">x</button>
                        </header>
                        <div class="game-unavailable-modal__body">
                            <h2 id="game-unavailable-modal-title">${escapeHtml(copy.title)}</h2>
                            <p>${escapeHtml(copy.body)}</p>
                        </div>
                        <footer class="game-unavailable-modal__actions">
                            <button class="game-action-button game-action-button--primary" type="button" onclick="this.closest('#game-modal-root').innerHTML = ''">Понятно</button>
                        </footer>
                    </section>
                </div>
            `;
        },

        closeHudWindow(name) {
            const hudWindow = this.windows[name];
            if (!hudWindow) return;
            hudWindow.open = false;
            saveHudOpenState(name, false);
        },

        startHudWindowDrag(name, event, element) {
            const hudWindow = this.windows[name];
            if (!hudWindow || !element) return;
            if (shellMetrics().isMobile) return;

            const rect = element.getBoundingClientRect();
            hudWindow.x = rect.left;
            hudWindow.y = rect.top;
            hudWindow.width = rect.width;
            hudWindow.height = rect.height;
            hudWindow.dragging = true;
            hudWindow.resizing = false;
            hudWindow.dragOffsetX = event.clientX - rect.left;
            hudWindow.dragOffsetY = event.clientY - rect.top;

            if (event.pointerId !== undefined && element.setPointerCapture) {
                element.setPointerCapture(event.pointerId);
            }
        },

        startHudWindowResize(name, edge, event, element) {
            const hudWindow = this.windows[name];
            if (!hudWindow || !element) return;
            if (shellMetrics().isMobile) return;

            const rect = element.getBoundingClientRect();
            hudWindow.x = rect.left;
            hudWindow.y = rect.top;
            hudWindow.width = rect.width;
            hudWindow.height = rect.height;
            hudWindow.dragging = false;
            hudWindow.resizing = true;
            hudWindow.resizeEdge = edge;
            hudWindow.resizeStartX = event.clientX;
            hudWindow.resizeStartY = event.clientY;
            hudWindow.resizeStartLeft = rect.left;
            hudWindow.resizeStartTop = rect.top;
            hudWindow.resizeStartWidth = rect.width;
            hudWindow.resizeStartHeight = rect.height;

            if (event.pointerId !== undefined && element.setPointerCapture) {
                element.setPointerCapture(event.pointerId);
            }
        },

        moveHudWindow(event) {
            for (const hudWindow of Object.values(this.windows)) {
                if (hudWindow.resizing) {
                    this.resizeHudWindow(hudWindow, event);
                    continue;
                }
                if (!hudWindow.dragging) continue;

                const metrics = shellMetrics();
                const width = hudWindow.width || 88;
                const height = hudWindow.height || 72;
                const maxX = Math.max(metrics.inset, window.innerWidth - width - metrics.inset);
                const maxY = Math.max(metrics.top, window.innerHeight - height - metrics.bottom);
                hudWindow.x = Math.max(metrics.inset, Math.min(maxX, event.clientX - hudWindow.dragOffsetX));
                hudWindow.y = Math.max(metrics.top, Math.min(maxY, event.clientY - hudWindow.dragOffsetY));
            }
        },

        startChatLauncherDrag(event, element) {
            if (!element) return;
            const rect = element.getBoundingClientRect();
            this.chatLauncher.x = rect.left;
            this.chatLauncher.y = rect.top;
            this.chatLauncher.dragging = true;
            this.chatLauncher.dragMoved = false;
            this.chatLauncher.dragOffsetX = event.clientX - rect.left;
            this.chatLauncher.dragOffsetY = event.clientY - rect.top;
            this.chatLauncher.startX = event.clientX;
            this.chatLauncher.startY = event.clientY;

            if (event.pointerId !== undefined && element.setPointerCapture) {
                element.setPointerCapture(event.pointerId);
            }
        },

        moveChatLauncher(event) {
            if (!this.chatLauncher.dragging) return;

            const metrics = shellMetrics();
            const size = 52;
            const nextX = event.clientX - this.chatLauncher.dragOffsetX;
            const nextY = event.clientY - this.chatLauncher.dragOffsetY;
            const maxX = Math.max(metrics.inset, window.innerWidth - size - metrics.inset);
            const maxY = Math.max(metrics.top, window.innerHeight - size - metrics.bottom);

            if (Math.abs(event.clientX - this.chatLauncher.startX) > 3 || Math.abs(event.clientY - this.chatLauncher.startY) > 3) {
                this.chatLauncher.dragMoved = true;
            }

            this.chatLauncher.x = Math.max(metrics.inset, Math.min(maxX, nextX));
            this.chatLauncher.y = Math.max(metrics.top, Math.min(maxY, nextY));
        },

        stopChatLauncherDrag() {
            this.chatLauncher.dragging = false;
        },

        resizeHudWindow(hudWindow, event) {
            const metrics = shellMetrics();
            const edge = hudWindow.resizeEdge || "";
            const deltaX = event.clientX - hudWindow.resizeStartX;
            const deltaY = event.clientY - hudWindow.resizeStartY;
            const minWidth = Math.min(560, Math.max(320, window.innerWidth - 24));
            const maxWidth = Math.max(minWidth, window.innerWidth - (metrics.inset * 2));
            const availableHeight = window.innerHeight - metrics.top - metrics.bottom;
            const minHeight = Math.min(520, Math.max(320, availableHeight));
            const maxHeight = Math.max(minHeight, availableHeight);

            let nextLeft = hudWindow.resizeStartLeft;
            let nextTop = hudWindow.resizeStartTop;
            let nextWidth = hudWindow.resizeStartWidth;
            let nextHeight = hudWindow.resizeStartHeight;

            if (edge.includes("e")) nextWidth = hudWindow.resizeStartWidth + deltaX;
            if (edge.includes("s")) nextHeight = hudWindow.resizeStartHeight + deltaY;
            if (edge.includes("w")) {
                nextWidth = hudWindow.resizeStartWidth - deltaX;
                nextLeft = hudWindow.resizeStartLeft + deltaX;
            }
            if (edge.includes("n")) {
                nextHeight = hudWindow.resizeStartHeight - deltaY;
                nextTop = hudWindow.resizeStartTop + deltaY;
            }

            nextWidth = Math.max(minWidth, Math.min(maxWidth, nextWidth));
            nextHeight = Math.max(minHeight, Math.min(maxHeight, nextHeight));
            if (edge.includes("w")) nextLeft = hudWindow.resizeStartLeft + hudWindow.resizeStartWidth - nextWidth;
            if (edge.includes("n")) nextTop = hudWindow.resizeStartTop + hudWindow.resizeStartHeight - nextHeight;

            hudWindow.x = Math.max(metrics.inset, Math.min(window.innerWidth - nextWidth - metrics.inset, nextLeft));
            hudWindow.y = Math.max(metrics.top, Math.min(window.innerHeight - nextHeight - metrics.bottom, nextTop));
            hudWindow.width = nextWidth;
            hudWindow.height = nextHeight;
        },

        stopHudWindowDrag() {
            for (const [name, hudWindow] of Object.entries(this.windows)) {
                if (hudWindow.dragging || hudWindow.resizing) {
                    saveHudGeometry(name, hudWindow);
                }
                hudWindow.dragging = false;
                hudWindow.resizing = false;
                hudWindow.resizeEdge = "";
            }
        },

        hudWindowStyle(name) {
            const hudWindow = this.windows[name];
            if (!hudWindow) return "";
            if (shellMetrics().isMobile) return "";
            const parts = [];
            if (hudWindow.x !== null) {
                parts.push(`left: ${hudWindow.x}px`, `top: ${hudWindow.y}px`, "right: auto", "bottom: auto");
            }
            if (hudWindow.width !== null) parts.push(`width: ${hudWindow.width}px`);
            if (hudWindow.height !== null) {
                if (name === 'chat' && this.chatStep === 0) {
                    // Minimized: let it collapse naturally
                } else {
                    parts.push(`height: ${hudWindow.height}px`);
                }
            }
            return parts.length ? `${parts.join("; ")};` : "";
        },

        chatLauncherStyle() {
            if (this.chatLauncher.x === null || this.chatLauncher.y === null) return "";
            return `left: ${this.chatLauncher.x}px; top: ${this.chatLauncher.y}px; right: auto; bottom: auto;`;
        },
    };
};
