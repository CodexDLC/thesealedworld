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

function initGameTooltips(root = document) {
    if (typeof tippy === 'undefined') return;
    const nodes = Array.from(root.querySelectorAll('[data-tippy-content]'));
    const tooltipContent = (node) => (node.getAttribute('data-tippy-content') || '').replace(/\\n/g, '\n').replace(/\s+\/\/\s+/g, '\n');
    nodes.forEach((node) => {
        node.removeAttribute('title');
        if (node._tippy) {
            node._tippy.setContent(tooltipContent(node));
        }
    });
    tippy(nodes.filter((node) => !node._tippy), {
        allowHTML: false,
        appendTo: document.body,
        content(reference) {
            return tooltipContent(reference);
        },
        delay: [120, 40],
        maxWidth: 320,
        theme: 'game-hint',
    });
}

let activeInventoryTooltipTrigger = null;

function inventoryTooltipHost() {
    let host = document.getElementById('inventory-tooltip-host');
    if (host) return host;

    host = document.createElement('div');
    host.id = 'inventory-tooltip-host';
    host.className = 'inventory-floating-tooltip inventory-floating-tooltip--js';
    host.setAttribute('role', 'tooltip');
    document.body.appendChild(host);
    return host;
}

function inventoryTooltipTemplate(trigger) {
    return trigger?.querySelector?.('.inventory-tooltip-template') || null;
}

function positionInventoryTooltip(host, event, trigger = activeInventoryTooltipTrigger) {
    const gap = 14;
    const margin = 12;
    const width = host.offsetWidth || 292;
    const height = host.offsetHeight || 220;
    const rect = trigger?.getBoundingClientRect?.();
    let left = rect ? rect.right + gap : event.clientX + gap;
    let top = rect ? rect.top : event.clientY - margin;

    if (left + width > window.innerWidth - margin) {
        left = rect ? rect.left - width - gap : event.clientX - width - gap;
    }
    if (top + height > window.innerHeight - margin) {
        top = window.innerHeight - height - margin;
    }

    host.style.left = `${Math.max(margin, left)}px`;
    host.style.top = `${Math.max(margin, top)}px`;
}

function showInventoryTooltip(trigger, event) {
    const template = inventoryTooltipTemplate(trigger);
    if (!template) return;

    const host = inventoryTooltipHost();
    activeInventoryTooltipTrigger = trigger;
    host.innerHTML = template.innerHTML;
    host.classList.add('is-visible');
    positionInventoryTooltip(host, event, trigger);
}

function hideInventoryTooltip() {
    const host = document.getElementById('inventory-tooltip-host');
    activeInventoryTooltipTrigger = null;
    if (!host) return;

    host.classList.remove('is-visible');
    host.innerHTML = '';
}

function initInventoryTooltips() {
    document.addEventListener('pointerover', (event) => {
        const trigger = event.target?.closest?.('[data-inventory-tooltip-trigger]');
        if (!trigger || trigger === activeInventoryTooltipTrigger) return;
        showInventoryTooltip(trigger, event);
    });

    document.addEventListener('pointermove', (event) => {
        if (!activeInventoryTooltipTrigger) return;
        if (!activeInventoryTooltipTrigger.isConnected) {
            hideInventoryTooltip();
            return;
        }
        positionInventoryTooltip(inventoryTooltipHost(), event, activeInventoryTooltipTrigger);
    });

    document.addEventListener('pointerout', (event) => {
        if (!activeInventoryTooltipTrigger) return;
        if (activeInventoryTooltipTrigger.contains(event.relatedTarget)) return;
        hideInventoryTooltip();
    });

    document.addEventListener('htmx:beforeSwap', () => hideInventoryTooltip());
}

window.initGameTooltips = initGameTooltips;

document.addEventListener('DOMContentLoaded', () => {
    initGameTooltips(document);
    initInventoryTooltips();
});

// ── Universal action feedback ───────────────────────────────────────────────
// HTMX requests can take long enough that a click feels lost. Mark the control
// immediately so every game action has visible acknowledgement before the swap.
function resolveActionFeedbackElement(source) {
    if (!source || !source.closest) return null;
    const control = source.closest('button, a, [role="button"], input[type="submit"], input[type="button"]');
    if (!control || control.matches('[data-action-feedback="off"]')) return null;
    return control;
}

function setActionFeedback(source) {
    const control = resolveActionFeedbackElement(source);
    if (!control) return;

    control.classList.add('is-action-pending');
    control.setAttribute('aria-busy', 'true');
    if (!control.hasAttribute('aria-live')) {
        control.setAttribute('aria-live', 'polite');
        control.dataset.actionFeedbackLive = 'true';
    }
}

function clearActionFeedback(source) {
    const control = resolveActionFeedbackElement(source);
    if (!control) return;

    control.classList.remove('is-action-pending');
    control.removeAttribute('aria-busy');
    if (control.dataset.actionFeedbackLive === 'true') {
        control.removeAttribute('aria-live');
        delete control.dataset.actionFeedbackLive;
    }
}

// ── HTMX hooks ───────────────────────────────────────────────────────────────
document.addEventListener('htmx:beforeRequest', (event) => {
    setActionFeedback(event.detail?.elt);
});

document.addEventListener('htmx:afterRequest', (event) => {
    clearActionFeedback(event.detail?.elt);
});

document.addEventListener('htmx:sendAbort', (event) => {
    clearActionFeedback(event.detail?.elt);
});

document.addEventListener('htmx:timeout', (event) => {
    clearActionFeedback(event.detail?.elt);
});

document.addEventListener('htmx:responseError', (event) => {
    clearActionFeedback(event.detail?.elt);
});

document.addEventListener('htmx:load', function() {
    if (window.GameCatalogCache) {
        window.GameCatalogCache.init().then(() => window.GameCatalogCache.resolveDom(document));
        return;
    }
    initGameTooltips(document);
});
