window.ExplorationMoveCooldown = {
    endAt: 0,
    durationMs: 0,
    timer: null,

    init(root = document) {
        this.apply(root);
    },

    isActive() {
        return Date.now() < this.endAt;
    },

    start(durationSeconds) {
        const duration = Number(durationSeconds);
        if (!Number.isFinite(duration) || duration <= 0) return;

        this.durationMs = Math.max(250, duration * 1000);
        this.endAt = Date.now() + this.durationMs;
        this.tick();

        if (this.timer) clearInterval(this.timer);
        this.timer = setInterval(() => this.tick(), 80);
    },

    tick() {
        const remaining = Math.max(0, this.endAt - Date.now());
        if (remaining <= 0) {
            this.clear();
            return;
        }

        const progress = Math.max(0, Math.min(1, 1 - remaining / this.durationMs));
        document.querySelectorAll('.exploration-movement-block, .mobile-move-cooldown').forEach((block) => {
            block.classList.add('is-cooling');
            block.style.setProperty('--move-cooldown-progress', progress.toFixed(3));
            const scope = block.closest('.exploration-action-panel') || block;
            scope.querySelectorAll('.dp[data-move-duration]').forEach((button) => {
                button.disabled = true;
                button.setAttribute('aria-disabled', 'true');
            });
            const label = block.querySelector('.exploration-move-cooldown-label') || scope.querySelector('.exploration-move-cooldown-label');
            if (label) label.textContent = `${(remaining / 1000).toFixed(1)}S`;
        });
    },

    clear() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
        this.endAt = 0;
        this.durationMs = 0;

        document.querySelectorAll('.exploration-movement-block, .mobile-move-cooldown').forEach((block) => {
            block.classList.remove('is-cooling');
            block.style.setProperty('--move-cooldown-progress', '1');
            const scope = block.closest('.exploration-action-panel') || block;
            scope.querySelectorAll('.dp[data-move-duration]').forEach((button) => {
                button.disabled = false;
                button.removeAttribute('aria-disabled');
            });
            const label = block.querySelector('.exploration-move-cooldown-label') || scope.querySelector('.exploration-move-cooldown-label');
            if (label) label.textContent = 'READY';
        });
    },

    apply(root = document) {
        if (!this.isActive()) {
            root.querySelectorAll?.('.exploration-move-cooldown-label').forEach((label) => {
                label.textContent = 'READY';
            });
            root.querySelectorAll?.('.exploration-movement-block, .mobile-move-cooldown').forEach((block) => {
                block.style.setProperty('--move-cooldown-progress', '1');
            });
            return;
        }
        this.tick();
    },
};

window.ExplorationRiskFrame = {
    init(root = document) {
        root.querySelectorAll?.('[data-risk-frame]').forEach((scene) => this.apply(scene));
    },

    apply(scene) {
        const isEncounter = scene.dataset.encounter === 'true';
        const isSafeZone = scene.dataset.safeZone === 'true';
        const threat = Math.max(0, Math.min(1, Number(scene.dataset.threat || 0)));

        let color;
        if (isEncounter) {
            color = [255, 58, 42];
        } else if (isSafeZone) {
            color = [70, 238, 142];
        } else if (threat < 0.5) {
            const t = threat / 0.5;
            color = this.mix([220, 184, 48], [230, 106, 28], t);
        } else {
            const t = (threat - 0.5) / 0.5;
            color = this.mix([230, 106, 28], [255, 58, 42], t);
        }

        scene.classList.toggle('is-danger', isEncounter || (!isSafeZone && threat >= 0.75));
        scene.classList.toggle('is-safe', isSafeZone && !isEncounter);
        scene.style.setProperty('--danger-color', `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.94)`);
        scene.style.setProperty('--danger-glow-color', `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.36)`);
    },

    mix(from, to, t) {
        return from.map((value, index) => Math.round(value + (to[index] - value) * t));
    },
};

document.addEventListener('click', (event) => {
    const button = event.target.closest?.('.dp[data-move-duration]');
    if (!button) return;

    if (window.ExplorationMoveCooldown.isActive()) {
        event.preventDefault();
        event.stopPropagation();
        return;
    }

    window.setTimeout(() => {
        window.ExplorationMoveCooldown.start(button.dataset.moveDuration);
    }, 0);
}, true);

document.addEventListener('DOMContentLoaded', () => {
    window.ExplorationMoveCooldown.init();
    window.ExplorationRiskFrame.init();
});

document.addEventListener('htmx:load', (event) => {
    window.ExplorationMoveCooldown.init(event.target);
    window.ExplorationRiskFrame.init(event.target);
});
