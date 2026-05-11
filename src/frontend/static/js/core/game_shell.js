window.inventoryGridLayout = function(element) {
    if (!element) return null;

    const root = element.closest(".inventory-shell") || element;
    const frame = element.closest(".inventory-window") || root;
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
    const loadHudOpenState = (name) => {
        try {
            const raw = window.localStorage.getItem(hudOpenStorageKey(name));
            if (!raw) return null;
            const saved = JSON.parse(raw);
            return typeof saved?.open === "boolean" ? saved.open : null;
        } catch (_error) {
            window.localStorage.removeItem(hudOpenStorageKey(name));
            return null;
        }
    };
    const saveHudOpenState = (name, isOpen) => {
        try {
            window.localStorage.setItem(hudOpenStorageKey(name), JSON.stringify({ open: Boolean(isOpen) }));
        } catch (_error) {
            return;
        }
    };
    const savedInventoryOpen = loadHudOpenState("inventory");
    const inventoryWindow = {
        open: Boolean(initial.initialInventoryOpen) && savedInventoryOpen !== false,
        x: null,
        y: null,
        width: null,
        height: null,
        dragging: false,
        resizing: false,
        resizeEdge: "",
        dragOffsetX: 0,
        dragOffsetY: 0,
        resizeStartX: 0,
        resizeStartY: 0,
        resizeStartLeft: 0,
        resizeStartTop: 0,
        resizeStartWidth: 0,
        resizeStartHeight: 0,
    };
    const loadHudGeometry = (name, target) => {
        try {
            const raw = window.localStorage.getItem(hudStorageKey(name));
            if (!raw) return;
            const saved = JSON.parse(raw);
            for (const key of ["x", "y", "width", "height"]) {
                if (Number.isFinite(saved[key])) target[key] = saved[key];
            }
        } catch (_error) {
            window.localStorage.removeItem(hudStorageKey(name));
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
    loadHudGeometry("inventory", inventoryWindow);
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

    return {
        chatTab: "global",
        chatHeight: Alpine.$persist(200),
        chatMinimized: Alpine.$persist(false),
        chatStep: Alpine.$persist(1),
        chatClosed: Alpine.$persist(false),
        chatUnread: false,
        selectedAgentId: activeCharId,
        domain,
        agents: {
            [activeCharId]: initial.initialStatus || {},
        },
        leftPanelView: "status",
        rightPanelView: "context",
        windows: {
            inventory: inventoryWindow,
        },
        chatLauncher,
        leftOpen: Boolean(initial.leftOpen),
        rightOpen: Boolean(initial.rightOpen),

        togglePanel(detail = {}) {
            if (detail.side === "left") {
                const nextView = detail.view || this.leftPanelView;
                if (this.leftOpen && this.leftPanelView === nextView) {
                    this.leftOpen = false;
                    return;
                }
                if (detail.view) this.leftPanelView = detail.view;
                this.leftOpen = true;
            }
            if (detail.side === "right") {
                const nextView = detail.view || this.rightPanelView;
                if (this.rightOpen && this.rightPanelView === nextView) {
                    this.rightOpen = false;
                    return;
                }
                if (detail.view) this.rightPanelView = detail.view;
                this.rightOpen = true;
            }
        },

        toggleHudWindow(name) {
            const hudWindow = this.windows[name];
            if (!hudWindow) return;
            hudWindow.open = !hudWindow.open;
            saveHudOpenState(name, hudWindow.open);
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
            if (hudWindow.height !== null) parts.push(`height: ${hudWindow.height}px`);
            return parts.length ? `${parts.join("; ")};` : "";
        },

        chatLauncherStyle() {
            if (this.chatLauncher.x === null || this.chatLauncher.y === null) return "";
            return `left: ${this.chatLauncher.x}px; top: ${this.chatLauncher.y}px; right: auto; bottom: auto;`;
        },
    };
};
