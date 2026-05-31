(function () {
    let activeInventoryTooltipTrigger = null;
    let activeInventoryMenuTrigger = null;
    let inventoryMenuLongPressTimer = null;
    let inventoryMenuSuppressNextClick = false;
    let listenersBound = false;

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
            item_id: action.item_id || trigger.dataset.inventoryItemId,
            tab_id: state.activeInventoryTab || 'items',
            slot_id: slotId || null,
        };
    }

    function positionInventoryContextMenu(host, event) {
        if (isTouchInventoryMode()) {
            positionInventoryTouchOverlay(host, activeInventoryMenuTrigger, 0.42);
            host.style.removeProperty('left');
            host.style.removeProperty('top');
            return;
        }

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

    function inventoryActionTarget(trigger) {
        const root = trigger.closest('.inventory-shell');
        return root?.dataset?.inventoryTarget || trigger.getAttribute('hx-target') || '#right-inventory-panel-body';
    }

    function runInventoryAction(trigger, action) {
        hideInventoryContextMenu();
        hideInventoryTooltip();
        if (!window.htmx) return;
        window.htmx.ajax('POST', '/game/inventory/action', {
            target: inventoryActionTarget(trigger),
            swap: trigger.getAttribute('hx-swap') || 'innerHTML',
            values: inventoryActionPayload(trigger, action),
        });
    }

    function inventoryActionForm(trigger, action, buttonClass, role = null) {
        const form = document.createElement('form');
        form.className = 'inventory-action-form';
        form.setAttribute('method', 'post');

        const button = document.createElement('button');
        button.type = 'button';
        button.className = buttonClass;
        button.textContent = action.label || inventoryActionLabel(action.action);
        if (role) {
            button.setAttribute('role', role);
        }

        if (action.enabled === false) {
            button.disabled = true;
            if (action.reason) {
                button.title = String(action.reason);
            }
            form.appendChild(button);
            return form;
        }

        let dispatched = false;
        const dispatchAction = (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (dispatched) return;
            dispatched = true;
            runInventoryAction(trigger, action);
            window.setTimeout(() => { dispatched = false; }, 400);
        };
        const stopActionEvent = (event) => {
            event.stopPropagation();
        };

        button.addEventListener('pointerdown', stopActionEvent, true);
        button.addEventListener('touchstart', stopActionEvent, { capture: true, passive: true });
        button.addEventListener('pointerup', (event) => {
            if (event.pointerType === 'mouse') return;
            dispatchAction(event);
        }, true);
        button.addEventListener('touchend', dispatchAction, true);
        button.addEventListener('click', dispatchAction);
        form.appendChild(button);
        return form;
    }

    function positionInventoryTouchOverlay(host, trigger, maxViewportRatio = 0.62) {
        if (!host || !trigger) return;

        const panel = trigger.closest('.right-inventory-panel') || trigger.closest('.col-right');
        const panelRect = panel?.getBoundingClientRect?.();
        const navRect = panel?.querySelector?.('.inventory-panel-actions')?.getBoundingClientRect?.();
        const margin = 8;
        const minOverlayWidth = Math.min(280, Math.max(220, window.innerWidth - (margin * 2)));
        const usePanelBounds = panelRect && panelRect.width >= minOverlayWidth;
        const topBase = navRect ? navRect.bottom : (panelRect ? panelRect.top + 45 : 0);
        const top = Math.max(margin, Math.round(topBase + 6));
        const left = usePanelBounds ? Math.max(margin, Math.round(panelRect.left + margin)) : margin;
        const right = usePanelBounds ? Math.max(margin, Math.round(window.innerWidth - panelRect.right + margin)) : margin;
        const availableHeight = Math.max(180, window.innerHeight - top - margin);
        const maxHeight = Math.max(180, Math.min(Math.round(window.innerHeight * maxViewportRatio), availableHeight));

        host.style.setProperty('--inventory-touch-overlay-top', `${top}px`);
        host.style.setProperty('--inventory-touch-overlay-left', `${left}px`);
        host.style.setProperty('--inventory-touch-overlay-right', `${right}px`);
        host.style.setProperty('--inventory-touch-overlay-max-height', `${maxHeight}px`);
    }

    function showInventoryContextMenu(trigger, event) {
        const actions = inventoryDatasetJson(trigger, 'inventoryActions', []);
        if (!Array.isArray(actions) || !actions.length) return;

        const host = inventoryContextMenuHost();
        activeInventoryMenuTrigger = trigger;
        host.innerHTML = '';
        actions.forEach((action) => {
            host.appendChild(inventoryActionForm(trigger, action, 'inventory-context-menu-action', 'menuitem'));
        });
        if (window.htmx) {
            window.htmx.process(host);
        }
        host.classList.add('is-visible');
        host.classList.toggle('inventory-context-menu--touch', isTouchInventoryMode());
        positionInventoryContextMenu(host, event);
    }

    function hideInventoryContextMenu() {
        const host = document.getElementById('inventory-context-menu-host');
        activeInventoryMenuTrigger = null;
        if (!host) return;
        host.classList.remove('is-visible');
        host.classList.remove('inventory-context-menu--touch');
        host.innerHTML = '';
    }

    function appendTouchInventoryActions(host, trigger) {
        if (!isTouchInventoryMode()) return;

        host.classList.add('inventory-floating-tooltip--touch');
        positionInventoryTouchOverlay(host, trigger);
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'inventory-tooltip-close';
        closeButton.setAttribute('aria-label', 'Close item card');
        closeButton.textContent = '×';
        closeButton.addEventListener('click', hideInventoryTooltip);
        host.prepend(closeButton);

        const menuActions = inventoryDatasetJson(trigger, 'inventoryActions', []);
        if (Array.isArray(menuActions) && menuActions.length) {
            const footer = document.createElement('div');
            footer.className = 'inventory-tooltip-actions inventory-tooltip-actions--multi';
            menuActions.forEach((action) => {
                footer.appendChild(inventoryActionForm(trigger, action, 'inventory-tooltip-action'));
            });
            host.appendChild(footer);
            if (window.htmx) {
                window.htmx.process(host);
            }
            return;
        }

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

        let dispatched = false;
        const dispatchAction = (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (dispatched) return;
            dispatched = true;
            hideInventoryTooltip();
            if (!window.htmx) return;
            window.htmx.ajax('POST', hxPost, {
                target: inventoryActionTarget(trigger),
                swap: trigger.getAttribute('hx-swap') || 'innerHTML',
                values: payload,
            });
            window.setTimeout(() => { dispatched = false; }, 400);
        };
        const stopActionEvent = (event) => {
            event.stopPropagation();
        };

        button.addEventListener('pointerdown', stopActionEvent, true);
        button.addEventListener('touchstart', stopActionEvent, { capture: true, passive: true });
        button.addEventListener('pointerup', (event) => {
            if (event.pointerType === 'mouse') return;
            dispatchAction(event);
        }, true);
        button.addEventListener('touchend', dispatchAction, true);
        button.addEventListener('click', dispatchAction);
        footer.appendChild(button);
        host.appendChild(footer);
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

    function bindInventoryListeners() {
        if (listenersBound) return;
        listenersBound = true;

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
        document.addEventListener('htmx:afterSwap', (event) => {
            if (event.detail?.target?.id !== 'right-inventory-panel-body') return;
            hideInventoryTooltip();
            hideInventoryContextMenu();
        });
    }

    window.GameStates = window.GameStates || {};
    window.GameStates.inventory = {
        init(root = document) {
            if (!root?.querySelector?.('.inventory-shell') && !root?.matches?.('.inventory-shell')) return;
            bindInventoryListeners();
        },
    };
})();
