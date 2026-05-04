/**
 * Character Status Polling & UI Sync
 * Handles real-time updates for HP, Energy, and Stamina.
 */

window.CharacterStatus = {
    pollingInterval: 3000, // 3 seconds
    timer: null,

    init() {
        console.log("CharacterStatus initialized");
        if (this.isCombatDomain()) {
            this.stopPolling();
            return;
        }
        this.startPolling();
    },

    startPolling() {
        if (this.isCombatDomain()) return;
        if (this.timer) return;
        this.timer = setInterval(() => this.updateStatus(), this.pollingInterval);
    },

    stopPolling() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    },

    async updateStatus() {
        if (this.isCombatDomain()) {
            this.stopPolling();
            return;
        }
        // Try to find selectedAgentId from Alpine state
        const container = document.querySelector('.game-container');
        if (!container || !window.Alpine) return;

        const data = Alpine.$data(container);
        const charId = data.selectedAgentId;

        if (!charId) return;

        try {
            const response = await fetch(`/api/game/character-status?char_id=${charId}`);
            if (!response.ok) throw new Error("Status update failed");

            const status = await response.json();

            // Update Alpine state
            if (data.agents && data.agents[charId]) {
                // We use Object.assign to keep reactivity and update multiple fields
                Object.assign(data.agents[charId], {
                    hp: status.hp,
                    max_hp: status.max_hp,
                    energy: status.energy,
                    max_energy: status.max_energy,
                    stamina: status.stamina,
                    max_stamina: status.max_stamina,
                    avatar_url: status.avatar_url || data.agents[charId].avatar_url
                });
            } else if (data.agents) {
                // Initialize if missing
                data.agents[charId] = status;
            }
        } catch (err) {
            console.warn("Status poll error:", err);
        }
    },

    isCombatDomain() {
        const container = document.querySelector('.game-container');
        if (!container) return false;
        if (container.dataset.domain === "COMBAT") return true;
        if (!window.Alpine) return false;
        const data = Alpine.$data(container);
        return data?.domain === "COMBAT";
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.CharacterStatus.init();
});

document.addEventListener('session:panel-state', (event) => {
    const container = document.querySelector('.game-container');
    if (!container || !window.Alpine) return;

    const data = Alpine.$data(container);
    if (!data) return;

    const state = event.detail?.value || event.detail || {};
    if (Object.prototype.hasOwnProperty.call(state, 'left_open')) {
        data.leftOpen = Boolean(state.left_open);
    }
    if (Object.prototype.hasOwnProperty.call(state, 'right_open')) {
        data.rightOpen = Boolean(state.right_open);
    }
});
