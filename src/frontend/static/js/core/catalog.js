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
            tooltipNodes.forEach((node) => {
                if (node._tippy) {
                    node._tippy.setContent(node.getAttribute('data-tippy-content'));
                }
            });
            tippy(Array.from(tooltipNodes).filter((node) => !node._tippy), {
                allowHTML: false,
                appendTo: document.body,
                delay: [120, 40],
                maxWidth: 320,
                theme: 'game-catalog'
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
