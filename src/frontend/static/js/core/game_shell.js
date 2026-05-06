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
    const inventoryWindow = {
        open: false,
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

    return {
        chatTab: "global",
        chatHeight: Alpine.$persist(200),
        chatMinimized: Alpine.$persist(false),
        chatStep: Alpine.$persist(1),
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

        resizeHudWindow(hudWindow, event) {
            const metrics = shellMetrics();
            const edge = hudWindow.resizeEdge || "";
            const deltaX = event.clientX - hudWindow.resizeStartX;
            const deltaY = event.clientY - hudWindow.resizeStartY;
            const minWidth = Math.min(720, Math.max(320, window.innerWidth - 24));
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
            for (const hudWindow of Object.values(this.windows)) {
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
    };
};
