/*
 * Compiled JS — DO NOT EDIT
 * Sources: core/main.js
 * Minified: False
 */







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
            if (window.matchMedia("(max-width: 767px)").matches) {
                data.chatClosed = clamped === 0;
                if (clamped > 0) data.chatUnread = false;
            }
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

window.initGameTooltips = initGameTooltips;

document.addEventListener('DOMContentLoaded', () => {
    initGameTooltips(document);
});




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
