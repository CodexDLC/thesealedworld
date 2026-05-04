// Main Game Logic & UI Interactions

// ── Chat step control ────────────────────────────────────────────────────────
// Steps: 0=collapsed(40px)  1=25vh  2=50vh  3=75vh
// Shared core — sets height directly so CSS transition fires cleanly
function _applyChatStep(newStep) {
    const container = document.querySelector('.game-container');
    const chatRow   = document.querySelector('.game-chat-row');
    if (!container || !chatRow) return;

    const available = window.innerHeight - 80;
    const steps = [
        68,                            // 0: mini strip — preview only, input hidden
        Math.round(available * 0.25),  // 1: quarter — input hover-reveal
        Math.round(available * 0.50),  // 2: half
        Math.round(available * 0.75),  // 3: three-quarters
    ];
    const clamped = Math.max(0, Math.min(steps.length - 1, newStep));
    const height  = steps[clamped];

    // Direct style → CSS transition animates this, no Alpine lag
    chatRow.style.height = height + 'px';

    // Sync Alpine once (persistence + reactive classes)
    if (window.Alpine) {
        const data = Alpine.$data(container);
        if (data) {
            data.chatStep      = clamped;
            data.chatHeight    = height;
            data.chatMinimized = (clamped === 0);
            container.style.setProperty('--chat-height', height + 'px');
        }
    }
}

// Called by ▼/▲ buttons: delta = -1 or +1
window.stepChatSize = function(dirOrTarget) {
    const container = document.querySelector('.game-container');
    let currentStep = 1;
    if (window.Alpine && container) {
        const data = Alpine.$data(container);
        if (data && data.chatStep !== undefined) currentStep = data.chatStep;
    }

    let newStep;
    if (dirOrTarget === 'min')      newStep = 0;
    else if (dirOrTarget === 'max') newStep = 3;
    else                            newStep = currentStep + dirOrTarget;

    _applyChatStep(newStep);
};

// Called by step-dot clicks: jump directly to a step
window.setChatStep = function(targetStep) {
    _applyChatStep(targetStep);
};

// ── HTMX hooks ───────────────────────────────────────────────────────────────
document.addEventListener('htmx:load', function() {
    if (window.GameCatalogCache) {
        window.GameCatalogCache.init().then(() => window.GameCatalogCache.resolveDom(document));
        return;
    }
    if (typeof tippy !== 'undefined') tippy('[data-tippy-content]');
});
