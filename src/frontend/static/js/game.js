/*
 * Compiled JS — DO NOT EDIT
 * Sources: core/catalog.js, core/exploration_cooldown.js, core/game_shell.js, core/main.js
 * Minified: False
 */


const GAME_CATALOG_DB = 'tbmmorpg-game-catalog';
const GAME_CATALOG_STORE = 'catalogs';
const GAME_CATALOG_META_KEY = '__manifest__';

function openGameCatalogDb() {
    return new Promise((resolve, reject) => {
        if (!('indexedDB' in window)) {
            reject(new Error('IndexedDB is unavailable'));
            return;
        }

        const request = indexedDB.open(GAME_CATALOG_DB, 1);
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains(GAME_CATALOG_STORE)) {
                db.createObjectStore(GAME_CATALOG_STORE);
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error || new Error('IndexedDB open failed'));
    });
}

function idbGet(db, key) {
    return new Promise((resolve, reject) => {
        const tx = db.transaction(GAME_CATALOG_STORE, 'readonly');
        const request = tx.objectStore(GAME_CATALOG_STORE).get(key);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error || new Error(`IndexedDB get failed: ${key}`));
    });
}

function idbPut(db, key, value) {
    return new Promise((resolve, reject) => {
        const tx = db.transaction(GAME_CATALOG_STORE, 'readwrite');
        tx.objectStore(GAME_CATALOG_STORE).put(value, key);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error || new Error(`IndexedDB put failed: ${key}`));
    });
}

window.GameCatalogCache = {
    db: null,
    memory: {},
    ready: null,

    async init() {
        if (this.ready) return this.ready;
        this.ready = this._init();
        return this.ready;
    },

    async _init() {
        try {
            this.db = await openGameCatalogDb();
            await this.ensureFresh();
            await this.resolveDom();
        } catch (err) {
            console.warn('Game catalog cache unavailable:', err);
        }
    },

    async ensureFresh() {
        if (!this.db) return;

        const response = await fetch('/game/catalog/bootstrap', {
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
        });
        if (!response.ok) throw new Error(`Catalog bootstrap failed: ${response.status}`);

        const payload = await response.json();
        const remoteManifest = payload.manifest || { version: payload.version, catalogs: {} };
        const localManifest = await idbGet(this.db, GAME_CATALOG_META_KEY);

        if (localManifest && this.manifestMatches(localManifest, remoteManifest)) {
            for (const name of Object.keys(remoteManifest.catalogs || {})) {
                const cached = await idbGet(this.db, name);
                if (cached) this.memory[name] = cached;
            }
            return;
        }

        for (const [name, catalog] of Object.entries(payload.catalogs || {})) {
            this.memory[name] = catalog;
            await idbPut(this.db, name, catalog);
        }
        await idbPut(this.db, GAME_CATALOG_META_KEY, remoteManifest);
    },

    get(catalog, key) {
        if (!key) return null;
        const direct = this.memory?.[catalog]?.[key];
        if (direct) return direct;
        if (key.startsWith('combat.')) {
            return this.memory?.combat_entries?.[key] || null;
        }
        return null;
    },

    getByKey(key) {
        if (!key) return null;
        if (key.startsWith('combat.')) {
            return this.memory?.combat_entries?.[key] || null;
        }
        for (const catalog of Object.values(this.memory || {})) {
            if (catalog && typeof catalog === 'object' && catalog[key]) return catalog[key];
        }
        return null;
    },

    getCombatTextTemplate(templateKey) {
        if (!templateKey) return null;
        return this.memory?.combat_text?.templates?.[templateKey] || null;
    },

    getCombatTextResource(resourceType, resourceId) {
        if (!resourceType || !resourceId) return null;
        const buckets = {
            feint: 'feints',
            basic_exchange: 'basic_exchanges',
            effect: 'effects',
            ability: 'abilities',
            death: 'deaths',
            trigger: 'triggers',
            gift: 'gifts',
            item: 'items',
        };
        const bucket = buckets[resourceType] || resourceType;
        return this.memory?.combat_text?.resources?.[bucket]?.[resourceId] || null;
    },

    renderTemplate(template, variables = {}) {
        return String(template || '').replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, (match, key) => {
            const value = variables[key];
            if (value === undefined || value === null) return match;
            return String(value);
        });
    },

    renderCombatText(templateKey, variables = {}) {
        const entry = this.getCombatTextTemplate(templateKey);
        if (!entry) return '';
        return this.renderTemplate(entry.template, variables);
    },

    getTaxonomyVariant(entry, taxonomy = 'humanoid') {
        const variants = entry?.taxonomy_variants || {};
        const selected = variants[taxonomy];
        if (selected) return selected;
        const fallback = entry?.default_taxonomy || 'humanoid';
        return variants[fallback] || variants.humanoid || null;
    },

    getField(entry, field, taxonomy = 'humanoid') {
        if (!entry || !field) return '';
        if (field.startsWith('taxonomy.')) {
            const variant = this.getTaxonomyVariant(entry, taxonomy);
            return this.getNested(variant, field.slice('taxonomy.'.length));
        }
        const direct = this.getNested(entry, field);
        if (direct !== undefined && direct !== null && direct !== '') return direct;
        const variant = this.getTaxonomyVariant(entry, taxonomy);
        return this.getNested(variant, field) || '';
    },

    getNested(value, path) {
        if (!value || !path) return value;
        return path.split('.').reduce((current, part) => {
            if (current && Object.prototype.hasOwnProperty.call(current, part)) return current[part];
            return undefined;
        }, value);
    },

    getEventTextVariants(entry, eventName, taxonomy = 'humanoid') {
        const variant = this.getTaxonomyVariant(entry, taxonomy);
        const selected = variant?.event_texts?.[eventName] || [];
        if (selected.length) return selected;
        const fallback = this.getTaxonomyVariant(entry, entry?.default_taxonomy || 'humanoid');
        return fallback?.event_texts?.[eventName] || [];
    },

    manifestMatches(localManifest, remoteManifest) {
        if (!localManifest || localManifest.version !== remoteManifest.version) return false;
        const localCatalogs = localManifest.catalogs || {};
        const remoteCatalogs = remoteManifest.catalogs || {};
        const remoteNames = Object.keys(remoteCatalogs);
        if (Object.keys(localCatalogs).length !== remoteNames.length) return false;
        return remoteNames.every((name) => localCatalogs[name] === remoteCatalogs[name]);
    },

    async resolveDom(root = document) {
        if (!this.db) return;
        const nodes = root.querySelectorAll('[data-catalog][data-catalog-key]');
        nodes.forEach((node) => {
            const catalog = node.dataset.catalog;
            const key = node.dataset.catalogKey;
            const field = node.dataset.catalogField;
            const tooltipField = node.dataset.catalogTooltip;
            const taxonomy = node.dataset.catalogTaxonomy || 'humanoid';
            const eventName = node.dataset.catalogEvent;
            const entry = this.get(catalog, key) || this.getByKey(key);

            if (!entry) {
                node.classList.add('catalog-missing');
                node.setAttribute('data-tippy-content', `DATA_MISSING: ${catalog}:${key}`);
                return;
            }

            if (eventName) {
                const variants = this.getEventTextVariants(entry, eventName, taxonomy);
                if (variants.length) node.textContent = variants[0];
            } else if (field) {
                const value = this.getField(entry, field, taxonomy);
                if (value) node.textContent = value;
            }
            if (tooltipField) {
                const tooltip = this.getField(entry, tooltipField, taxonomy);
                if (tooltip) node.setAttribute('data-tippy-content', tooltip);
            }
        });

        if (typeof tippy !== 'undefined') {
            const tooltipNodes = root.querySelectorAll('[data-tippy-content]');
            const tooltipContent = (node) => (node.getAttribute('data-tippy-content') || '').replace(/\\n/g, '\n').replace(/\s+\/\/\s+/g, '\n');
            tooltipNodes.forEach((node) => {
                node.removeAttribute('title');
                if (node._tippy) {
                    node._tippy.setContent(tooltipContent(node));
                }
            });
            Array.from(tooltipNodes).filter((node) => !node._tippy).forEach((node) => {
                tippy(node, {
                    allowHTML: false,
                    appendTo: document.body,
                    content(reference) {
                        return tooltipContent(reference);
                    },
                    delay: [120, 40],
                    maxWidth: 320,
                    theme: node.getAttribute('data-tippy-theme') || 'game-catalog',
                });
            });
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.GameCatalogCache.init();
});

document.addEventListener('htmx:load', (event) => {
    window.GameCatalogCache.init().then(() => window.GameCatalogCache.resolveDom(event.target));
});



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



window.inventoryGridLayout = function(element) {
    if (!element) return null;

    const root = element.closest(".inventory-shell") || element;
    const frame = element.closest(".right-inventory-panel") || root;
    const readNumber = (value, fallback) => {
        const parsed = Number.parseFloat(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    };

    const update = () => {
        const styles = window.getComputedStyle(root);
        const gap = readNumber(styles.getPropertyValue("--inventory-grid-gap"), 5);
        const baseCell = readNumber(styles.getPropertyValue("--inventory-grid-base-cell"), 34);
        const cols = Math.max(1, Math.round(readNumber(styles.getPropertyValue("--inventory-grid-cols"), 12)));
        const extraRows = Math.max(0, Math.round(readNumber(styles.getPropertyValue("--inventory-grid-extra-rows"), 2)));
        const width = Math.max(0, frame.clientWidth - 48);
        if (width <= 0) return;

        const cell = Math.max(22, Math.min(baseCell, (width - gap * (cols - 1)) / cols));
        const capacity = Math.max(1, Math.ceil(readNumber(element.dataset.inventoryCells, cols * 5)));
        const rows = Math.max(1, Math.ceil(capacity / cols) + extraRows);
        const framePadding = 16;
        const gridWidth = cols * cell + gap * Math.max(0, cols - 1) + framePadding;
        const gridHeight = rows * cell + gap * Math.max(0, rows - 1);
        const viewportHeight = Math.min(gridHeight, Math.max(cell * 5, frame.clientHeight * 0.42));
        root.style.setProperty("--inventory-cell", `${cell}px`);
        root.style.setProperty("--inventory-grid-rows", String(rows));
        root.style.setProperty("--inventory-grid-width", `${gridWidth}px`);
        root.style.setProperty("--inventory-grid-height", `${gridHeight}px`);
        root.style.setProperty("--inventory-grid-viewport-height", `${viewportHeight}px`);
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(frame);
    window.addEventListener("resize", update, { passive: true });
    return () => {
        observer.disconnect();
        window.removeEventListener("resize", update);
    };
};

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
    const hudStorageKey = (name) => `tbmmorpg:hud:${name}:geometry:v1`;
    const hudOpenStorageKey = (name) => {
        const scope = activeCharId || "global";
        return `tbmmorpg:hud:${name}:open:${scope}:v1`;
    };
    const panelStateStorageKey = () => {
        const scope = activeCharId || "global";
        const domainScope = domain || "global";
        const viewportScope = isDrawerViewport() ? "drawer" : "desktop";
        return `tbmmorpg:shell:panels:${domainScope}:${scope}:${viewportScope}:v1`;
    };
    const isDrawerViewport = () => window.matchMedia("(max-width: 1024px)").matches;
    const clearDrawerPanelState = () => {
        try {
            window.localStorage.removeItem(panelStateStorageKey());
        } catch (_error) {
            return;
        }
    };
    const explorationDesktopPanelsDefaultOpen = () => {
        if (domain !== "exploration") return false;
        return window.matchMedia("(min-width: 1025px)").matches;
    };
    const unavailableModalCopy = {
        quests: {
            eyebrow: "QUEST SYSTEM",
            title: "Система квестов будет доступна позже",
            body: "Этот раздел сейчас в разработке. Когда он будет готов, здесь появятся активные задачи, следы, цепочки событий и журнал решений.",
        },
    };
    const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
    })[char]);
    const noInventoryDomains = ["combats", "death", "loot"];
    const loadPanelState = () => {
        if (isDrawerViewport()) {
            clearDrawerPanelState();
            return null;
        }
        try {
            const raw = window.localStorage.getItem(panelStateStorageKey());
            if (!raw) return null;
            const saved = JSON.parse(raw);
            if (typeof saved?.leftOpen !== "boolean" || typeof saved?.rightOpen !== "boolean") return null;
            const savedRightView = typeof saved.rightPanelView === "string" ? saved.rightPanelView : "context";
            return {
                leftOpen: saved.leftOpen,
                rightOpen: saved.rightOpen,
                leftPanelView: typeof saved.leftPanelView === "string" ? saved.leftPanelView : "status",
                rightPanelView: noInventoryDomains.includes(domain) ? "context" : savedRightView,
            };
        } catch (_error) {
            window.localStorage.removeItem(panelStateStorageKey());
            return null;
        }
    };
    const savePanelState = (state) => {
        if (isDrawerViewport()) {
            clearDrawerPanelState();
            return;
        }
        try {
            window.localStorage.setItem(panelStateStorageKey(), JSON.stringify({
                leftOpen: Boolean(state.leftOpen),
                rightOpen: Boolean(state.rightOpen),
                leftPanelView: state.leftPanelView || "status",
                rightPanelView: state.rightPanelView || "context",
            }));
        } catch (_error) {
            return;
        }
    };
    const saveHudOpenState = (name, isOpen) => {
        try {
            window.localStorage.setItem(hudOpenStorageKey(name), JSON.stringify({ open: Boolean(isOpen) }));
        } catch (_error) {
            return;
        }
    };
    const saveHudGeometry = (name, hudWindow) => {
        if (hudWindow.x === null || hudWindow.y === null || hudWindow.width === null || hudWindow.height === null) {
            return;
        }
        window.localStorage.setItem(hudStorageKey(name), JSON.stringify({
            x: Math.round(hudWindow.x),
            y: Math.round(hudWindow.y),
            width: Math.round(hudWindow.width),
            height: Math.round(hudWindow.height),
        }));
    };
    const savedPanelState = loadPanelState();
    const defaultPanelsOpen = explorationDesktopPanelsDefaultOpen();
    const initialPanelState = savedPanelState || {
        leftOpen: !isDrawerViewport() && defaultPanelsOpen,
        rightOpen: !isDrawerViewport() && defaultPanelsOpen,
        leftPanelView: "status",
        rightPanelView: "context",
    };
    const chatLauncher = {
        x: null,
        y: null,
        dragging: false,
        dragMoved: false,
        dragOffsetX: 0,
        dragOffsetY: 0,
        startX: 0,
        startY: 0,
    };

    return {
        chatTab: "global",
        chatHeight: 30,
        chatMinimized: true,
        chatStep: 0,
        chatClosed: false,
        chatUnread: false,
        selectedAgentId: activeCharId,
        domain,
        agents: {
            [activeCharId]: initial.initialStatus || {},
        },
        leftPanelView: initialPanelState.leftPanelView,
        rightPanelView: initialPanelState.rightPanelView,
        panelStateUserEdited: savedPanelState !== null,
        windows: {},
        chatLauncher,
        leftOpen: initialPanelState.leftOpen,
        rightOpen: initialPanelState.rightOpen,

        togglePanel(detail = {}) {
            if (detail.side === "left") {
                const nextView = detail.view || this.leftPanelView;
                if (!detail.forceOpen && this.leftOpen && this.leftPanelView === nextView) {
                    this.leftOpen = false;
                    this.panelStateUserEdited = true;
                    savePanelState(this);
                    return;
                }
                if (detail.view) this.leftPanelView = detail.view;
                this.leftOpen = true;
                this.panelStateUserEdited = true;
                savePanelState(this);
            }
            if (detail.side === "right") {
                const nextView = detail.view || this.rightPanelView;
                if (!detail.forceOpen && this.rightOpen && this.rightPanelView === nextView) {
                    this.rightOpen = false;
                    this.panelStateUserEdited = true;
                    savePanelState(this);
                    return;
                }
                if (detail.view) this.rightPanelView = detail.view;
                this.rightOpen = true;
                this.panelStateUserEdited = true;
                savePanelState(this);
            }
        },

        toggleHudWindow(name) {
            const hudWindow = this.windows[name];
            if (!hudWindow) return;
            hudWindow.open = !hudWindow.open;
            saveHudOpenState(name, hudWindow.open);
        },

        openUnavailableModal(detail = {}) {
            const modalRoot = document.getElementById("game-modal-root");
            if (!modalRoot) return;

            const copy = unavailableModalCopy[detail.kind] || {
                eyebrow: "SYSTEM",
                title: "Система будет доступна позже",
                body: "Этот функционал сейчас находится в разработке.",
            };
            modalRoot.innerHTML = `
                <div class="game-modal-backdrop" role="presentation" onclick="if (event.target === this) this.closest('#game-modal-root').innerHTML = ''">
                    <section class="game-unavailable-modal" role="dialog" aria-modal="true" aria-labelledby="game-unavailable-modal-title">
                        <header class="game-unavailable-modal__head">
                            <span>${escapeHtml(copy.eyebrow)}</span>
                            <button class="game-modal-close" type="button" aria-label="Close modal" onclick="this.closest('#game-modal-root').innerHTML = ''">x</button>
                        </header>
                        <div class="game-unavailable-modal__body">
                            <h2 id="game-unavailable-modal-title">${escapeHtml(copy.title)}</h2>
                            <p>${escapeHtml(copy.body)}</p>
                        </div>
                        <footer class="game-unavailable-modal__actions">
                            <button class="game-action-button game-action-button--primary" type="button" onclick="this.closest('#game-modal-root').innerHTML = ''">Понятно</button>
                        </footer>
                    </section>
                </div>
            `;
        },

        closeHudWindow(name) {
            const hudWindow = this.windows[name];
            if (!hudWindow) return;
            hudWindow.open = false;
            saveHudOpenState(name, false);
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

        startChatLauncherDrag(event, element) {
            if (!element) return;
            const rect = element.getBoundingClientRect();
            this.chatLauncher.x = rect.left;
            this.chatLauncher.y = rect.top;
            this.chatLauncher.dragging = true;
            this.chatLauncher.dragMoved = false;
            this.chatLauncher.dragOffsetX = event.clientX - rect.left;
            this.chatLauncher.dragOffsetY = event.clientY - rect.top;
            this.chatLauncher.startX = event.clientX;
            this.chatLauncher.startY = event.clientY;

            if (event.pointerId !== undefined && element.setPointerCapture) {
                element.setPointerCapture(event.pointerId);
            }
        },

        moveChatLauncher(event) {
            if (!this.chatLauncher.dragging) return;

            const metrics = shellMetrics();
            const size = 52;
            const nextX = event.clientX - this.chatLauncher.dragOffsetX;
            const nextY = event.clientY - this.chatLauncher.dragOffsetY;
            const maxX = Math.max(metrics.inset, window.innerWidth - size - metrics.inset);
            const maxY = Math.max(metrics.top, window.innerHeight - size - metrics.bottom);

            if (Math.abs(event.clientX - this.chatLauncher.startX) > 3 || Math.abs(event.clientY - this.chatLauncher.startY) > 3) {
                this.chatLauncher.dragMoved = true;
            }

            this.chatLauncher.x = Math.max(metrics.inset, Math.min(maxX, nextX));
            this.chatLauncher.y = Math.max(metrics.top, Math.min(maxY, nextY));
        },

        stopChatLauncherDrag() {
            this.chatLauncher.dragging = false;
        },

        resizeHudWindow(hudWindow, event) {
            const metrics = shellMetrics();
            const edge = hudWindow.resizeEdge || "";
            const deltaX = event.clientX - hudWindow.resizeStartX;
            const deltaY = event.clientY - hudWindow.resizeStartY;
            const minWidth = Math.min(560, Math.max(320, window.innerWidth - 24));
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
            for (const [name, hudWindow] of Object.entries(this.windows)) {
                if (hudWindow.dragging || hudWindow.resizing) {
                    saveHudGeometry(name, hudWindow);
                }
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

        chatLauncherStyle() {
            if (this.chatLauncher.x === null || this.chatLauncher.y === null) return "";
            return `left: ${this.chatLauncher.x}px; top: ${this.chatLauncher.y}px; right: auto; bottom: auto;`;
        },
    };
};








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

let activeInventoryTooltipTrigger = null;

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

function initInventoryTooltips() {
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

    document.addEventListener('htmx:beforeSwap', () => hideInventoryTooltip());
}

window.initGameTooltips = initGameTooltips;

document.addEventListener('DOMContentLoaded', () => {
    initGameTooltips(document);
    initInventoryTooltips();
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
