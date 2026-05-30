// Main Game Logic & UI Interactions

// ── Chat step control ────────────────────────────────────────────────────────
// Steps: 0=footer height  1=25vh  2=50vh  3=75vh
// Shared core — sets height directly so CSS transition fires cleanly
function _applyChatStep(newStep) {
    const container = document.querySelector('.game-container');
    const chatRow   = document.querySelector('.game-chat-row');
    if (!container || !chatRow) return;

    const styles = window.getComputedStyle(container);
    const footerHeight = Number.parseFloat(styles.getPropertyValue('--game-footer-height')) || 30;
    const available = window.innerHeight - 80;
    const steps = [
        footerHeight,
        Math.round(available * 0.25),
        Math.round(available * 0.50),
        Math.round(available * 0.75),
    ];
    const clamped = Math.max(0, Math.min(steps.length - 1, newStep));
    const height  = steps[clamped];
    const minMaxLabel = clamped === 0 ? 'MAX' : 'MIN';

    chatRow.classList.remove('chat-step-0', 'chat-step-1', 'chat-step-2', 'chat-step-3', 'chat-minimized');
    chatRow.classList.add(`chat-step-${clamped}`);
    chatRow.classList.toggle('chat-minimized', clamped === 0);
    chatRow.querySelectorAll('[data-chat-minmax-label]').forEach((node) => {
        node.textContent = minMaxLabel;
    });
    container.style.setProperty('--chat-height', height + 'px');

    if (clamped === 0) {
        chatRow.style.removeProperty('height');
    } else {
        chatRow.style.height = height + 'px';
    }

    if (window.Alpine) {
        const data = Alpine.$data(container);
        if (data) {
            data.chatStep      = clamped;
            data.chatHeight    = height;
            data.chatMinimized = (clamped === 0);
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

window.toggleChatMinMax = function() {
    const container = document.querySelector('.game-container');
    let currentStep = 0;
    if (window.Alpine && container) {
        const data = Alpine.$data(container);
        if (data && data.chatStep !== undefined) currentStep = data.chatStep;
    }
    _applyChatStep(currentStep === 0 ? 3 : 0);
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
let activeInventoryMenuTrigger = null;
let inventoryMenuLongPressTimer = null;
let inventoryMenuSuppressNextClick = false;

function isTouchInventoryMode() {
    return window.matchMedia?.('(hover: none), (pointer: coarse)')?.matches || false;
}

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

function inventoryActionLabel(action) {
    return {
        equip: 'НАДЕТЬ',
        unequip: 'СНЯТЬ',
        move_to_belt: 'В ПОЯС',
        remove_from_belt: 'УБРАТЬ',
        use: 'ИСПОЛЬЗОВАТЬ',
        drop: 'ВЫБРОСИТЬ',
    }[action] || 'ДЕЙСТВИЕ';
}

function inventoryContextMenuHost() {
    let host = document.getElementById('inventory-context-menu-host');
    if (host) return host;

    host = document.createElement('div');
    host.id = 'inventory-context-menu-host';
    host.className = 'inventory-context-menu';
    host.setAttribute('role', 'menu');
    document.body.appendChild(host);
    return host;
}

function inventoryDatasetJson(trigger, key, fallback) {
    const raw = trigger?.dataset?.[key];
    if (!raw) return fallback;
    try {
        return JSON.parse(raw);
    } catch (_error) {
        return fallback;
    }
}

function inventoryAlpineState(trigger) {
    const root = trigger?.closest?.('.inventory-shell');
    if (!root || !window.Alpine?.$data) return {};
    try {
        return window.Alpine.$data(root) || {};
    } catch (_error) {
        return {};
    }
}

function inventoryActionPayload(trigger, action) {
    const state = inventoryAlpineState(trigger);
    const validSlots = inventoryDatasetJson(trigger, 'inventoryValidSlots', []);
    const selectedSlot = state.selectedSlot || null;
    const actionId = String(action.action || '');
    const slotId = (
        actionId === 'equip'
        && selectedSlot
        && Array.isArray(validSlots)
        && validSlots.includes(selectedSlot)
    ) ? selectedSlot : action.slot_id;
    return {
        char_id: Number(trigger.dataset.inventoryCharId),
        action: actionId,
        item_id: trigger.dataset.inventoryItemId,
        tab_id: state.activeInventoryTab || 'items',
        slot_id: slotId || null,
    };
}

function positionInventoryContextMenu(host, event) {
    const margin = 8;
    const width = host.offsetWidth || 176;
    const height = host.offsetHeight || 120;
    let left = event.clientX;
    let top = event.clientY;
    if (left + width > window.innerWidth - margin) {
        left = window.innerWidth - width - margin;
    }
    if (top + height > window.innerHeight - margin) {
        top = window.innerHeight - height - margin;
    }
    host.style.left = `${Math.max(margin, left)}px`;
    host.style.top = `${Math.max(margin, top)}px`;
}

function runInventoryMenuAction(trigger, action) {
    const root = trigger.closest('.inventory-shell');
    const target = root?.dataset?.inventoryTarget || trigger.getAttribute('hx-target') || '#right-inventory-panel-body';
    hideInventoryContextMenu();
    hideInventoryTooltip();
    if (!window.htmx) return;
    window.htmx.ajax('POST', '/game/inventory/action', {
        target,
        swap: 'innerHTML',
        values: inventoryActionPayload(trigger, action),
    });
}

function showInventoryContextMenu(trigger, event) {
    const actions = inventoryDatasetJson(trigger, 'inventoryActions', []);
    if (!Array.isArray(actions) || !actions.length) return;

    const host = inventoryContextMenuHost();
    activeInventoryMenuTrigger = trigger;
    host.innerHTML = '';
    actions.forEach((action) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'inventory-context-menu-action';
        button.setAttribute('role', 'menuitem');
        button.textContent = action.label || inventoryActionLabel(action.action);
        if (action.enabled === false) {
            button.disabled = true;
            if (action.reason) {
                button.title = String(action.reason);
            }
        } else {
            button.addEventListener('click', () => runInventoryMenuAction(trigger, action));
        }
        host.appendChild(button);
    });
    host.classList.add('is-visible');
    positionInventoryContextMenu(host, event);
}

function hideInventoryContextMenu() {
    const host = document.getElementById('inventory-context-menu-host');
    activeInventoryMenuTrigger = null;
    if (!host) return;
    host.classList.remove('is-visible');
    host.innerHTML = '';
}

function appendTouchInventoryActions(host, trigger) {
    if (!isTouchInventoryMode()) return;

    host.classList.add('inventory-floating-tooltip--touch');
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'inventory-tooltip-close';
    closeButton.setAttribute('aria-label', 'Close item card');
    closeButton.textContent = '×';
    closeButton.addEventListener('click', hideInventoryTooltip);
    host.prepend(closeButton);

    const hxPost = trigger.getAttribute('hx-post');
    const hxVals = trigger.getAttribute('hx-vals');
    if (!hxPost || !hxVals) return;

    let payload = {};
    try {
        payload = JSON.parse(hxVals);
    } catch (_error) {
        return;
    }

    const footer = document.createElement('div');
    footer.className = 'inventory-tooltip-actions';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'inventory-tooltip-action';
    button.textContent = inventoryActionLabel(payload.action);
    button.setAttribute('hx-post', hxPost);
    button.setAttribute('hx-target', trigger.getAttribute('hx-target') || '#right-inventory-panel-body');
    button.setAttribute('hx-swap', trigger.getAttribute('hx-swap') || 'innerHTML');
    button.setAttribute('hx-vals', hxVals);
    footer.appendChild(button);
    host.appendChild(footer);

    if (window.htmx) {
        window.htmx.process(host);
    }
}

function positionInventoryTooltip(host, event, trigger = activeInventoryTooltipTrigger) {
    if (host.classList.contains('inventory-floating-tooltip--touch')) return;

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
    host.classList.remove('inventory-floating-tooltip--touch');
    host.classList.add('is-visible');
    appendTouchInventoryActions(host, trigger);
    positionInventoryTooltip(host, event, trigger);
}

function hideInventoryTooltip() {
    const host = document.getElementById('inventory-tooltip-host');
    activeInventoryTooltipTrigger = null;
    if (!host) return;

    host.classList.remove('is-visible');
    host.classList.remove('inventory-floating-tooltip--touch');
    host.innerHTML = '';
}

function clearInventoryLongPress() {
    if (!inventoryMenuLongPressTimer) return;
    window.clearTimeout(inventoryMenuLongPressTimer);
    inventoryMenuLongPressTimer = null;
}

function initInventoryTooltips() {
    document.addEventListener('contextmenu', (event) => {
        const trigger = event.target?.closest?.('[data-inventory-menu-trigger]');
        if (!trigger) return;
        event.preventDefault();
        event.stopPropagation();
        hideInventoryTooltip();
        showInventoryContextMenu(trigger, event);
    });

    document.addEventListener('pointerdown', (event) => {
        if (!isTouchInventoryMode() || event.pointerType === 'mouse') return;
        const trigger = event.target?.closest?.('[data-inventory-menu-trigger]');
        if (!trigger) return;
        clearInventoryLongPress();
        inventoryMenuLongPressTimer = window.setTimeout(() => {
            inventoryMenuSuppressNextClick = true;
            hideInventoryTooltip();
            showInventoryContextMenu(trigger, event);
        }, 520);
    }, true);

    document.addEventListener('pointerup', clearInventoryLongPress, true);
    document.addEventListener('pointercancel', clearInventoryLongPress, true);
    document.addEventListener('scroll', () => {
        clearInventoryLongPress();
        hideInventoryContextMenu();
    }, true);

    document.addEventListener('click', (event) => {
        if (inventoryMenuSuppressNextClick) {
            inventoryMenuSuppressNextClick = false;
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        if (!activeInventoryMenuTrigger) return;
        if (event.target?.closest?.('#inventory-context-menu-host')) return;
        hideInventoryContextMenu();
    }, true);

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            hideInventoryContextMenu();
            hideInventoryTooltip();
        }
    });

    document.addEventListener('pointerover', (event) => {
        if (isTouchInventoryMode() || event.pointerType === 'touch' || event.pointerType === 'pen') return;
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

    document.addEventListener('click', (event) => {
        if (!isTouchInventoryMode()) return;
        if (event.target?.closest?.('#inventory-tooltip-host')) return;

        const trigger = event.target?.closest?.('[data-inventory-tooltip-trigger]');
        if (!trigger || !inventoryTooltipTemplate(trigger)) {
            hideInventoryTooltip();
            return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();
        showInventoryTooltip(trigger, event);
    }, true);

    document.addEventListener('htmx:beforeSwap', () => {
        hideInventoryTooltip();
        hideInventoryContextMenu();
    });
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
    handleSessionReplaced(event);
});

document.addEventListener('htmx:afterRequest', (event) => {
    handleSessionReplaced(event);
});

let sessionReplacedHandled = false;

function handleSessionReplaced(event) {
    if (sessionReplacedHandled) return;
    const xhr = event.detail?.xhr;
    if (!xhr || xhr.status !== 409) return;
    const trigger = (xhr.getResponseHeader && xhr.getResponseHeader('HX-Trigger')) || '';
    if (!trigger.includes('session-replaced')) return;
    sessionReplacedHandled = true;
    try {
        const detail = event.detail;
        if (detail) {
            detail.shouldSwap = false;
            detail.isError = false;
        }
    } catch (e) { /* noop */ }
    const target = '/game-lobby?reason=session_replaced';
    if (window.location.pathname + window.location.search !== target) {
        window.location.replace(target);
    }
}

document.addEventListener('htmx:load', function() {
    if (window.GameCatalogCache) {
        window.GameCatalogCache.init().then(() => window.GameCatalogCache.resolveDom(document));
        return;
    }
    initGameTooltips(document);
});
