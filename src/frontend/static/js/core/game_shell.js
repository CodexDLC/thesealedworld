window.gameShell = function(initial = {}) {
    const activeCharId = initial.activeCharId || "";
    const domain = initial.domain || "";
    const inventoryWindow = {
        open: false,
        x: null,
        y: null,
        dragging: false,
        dragOffsetX: 0,
        dragOffsetY: 0,
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

            const rect = element.getBoundingClientRect();
            hudWindow.x = rect.left;
            hudWindow.y = rect.top;
            hudWindow.dragging = true;
            hudWindow.dragOffsetX = event.clientX - rect.left;
            hudWindow.dragOffsetY = event.clientY - rect.top;

            if (event.pointerId !== undefined && element.setPointerCapture) {
                element.setPointerCapture(event.pointerId);
            }
        },

        moveHudWindow(event) {
            for (const hudWindow of Object.values(this.windows)) {
                if (!hudWindow.dragging) continue;

                const maxX = Math.max(8, window.innerWidth - 88);
                const maxY = Math.max(48, window.innerHeight - 72);
                hudWindow.x = Math.max(8, Math.min(maxX, event.clientX - hudWindow.dragOffsetX));
                hudWindow.y = Math.max(48, Math.min(maxY, event.clientY - hudWindow.dragOffsetY));
            }
        },

        stopHudWindowDrag() {
            for (const hudWindow of Object.values(this.windows)) {
                hudWindow.dragging = false;
            }
        },

        hudWindowStyle(name) {
            const hudWindow = this.windows[name];
            if (!hudWindow || hudWindow.x === null) return "";
            return `left: ${hudWindow.x}px; top: ${hudWindow.y}px; right: auto; bottom: auto;`;
        },
    };
};
