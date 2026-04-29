/*
 * Compiled JS — DO NOT EDIT
 * Sources: core/main.js
 * Minified: False
 */







function _applyChatStep(newStep) {
    const container = document.querySelector('.game-container');
    const chatRow   = document.querySelector('.game-chat-row');
    if (!container || !chatRow) return;

    const available = window.innerHeight - 80;
    const steps = [
        68,
        Math.round(available * 0.25),
        Math.round(available * 0.50),
        Math.round(available * 0.75),
    ];
    const clamped = Math.max(0, Math.min(steps.length - 1, newStep));
    const height  = steps[clamped];


    chatRow.style.height = height + 'px';


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


window.setChatStep = function(targetStep) {
    _applyChatStep(targetStep);
};


document.addEventListener('htmx:load', function() {
    if (typeof tippy !== 'undefined') tippy('[data-tippy-content]');
});
