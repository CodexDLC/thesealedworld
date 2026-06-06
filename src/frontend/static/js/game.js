/*
 * Compiled JS — DO NOT EDIT
 * Sources: core/catalog.js, core/exploration_cooldown.js, core/game_state_loader.js, core/game_shell.js, core/main.js
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

    formatFeintTooltip(entry, taxonomy = 'humanoid') {
        if (!entry) return '';
        const title = this.escapeHtml(this.getField(entry, 'title', taxonomy) || this.getField(entry, 'label', taxonomy) || '');
        const description = this.escapeHtml(this.getField(entry, 'long_description', taxonomy) || this.getField(entry, 'description', taxonomy) || '');
        const cost = this.renderFeintCost(entry.cost);
        const badges = this.renderFeintBadges(entry);
        const parts = [];
        if (title) parts.push(`<div class="combat-feint-tip__title">${title}</div>`);
        if (cost) parts.push(`<div class="combat-feint-tip__row combat-feint-tip__cost">${cost}</div>`);
        if (badges) parts.push(`<div class="combat-feint-tip__row combat-feint-tip__badges">${badges}</div>`);
        if (description) parts.push(`<div class="combat-feint-tip__body">${description}</div>`);
        return `<div class="combat-feint-tip">${parts.join('')}</div>`;
    },

    renderFeintCost(cost) {
        if (!cost || typeof cost !== 'object') return '';
        const tactics = cost.tactics || {};
        const items = Object.entries(tactics).filter(([, amount]) => amount);
        if (!items.length) return '<span class="combat-feint-tip__cost-empty">Без стоимости</span>';
        const chips = items.map(([token, amount]) => {
            const icon = this.tokenIconFile(token);
            const label = this.escapeHtml(this.formatCombatToken(token));
            return `<span class="combat-feint-tip__chip" data-token="${this.escapeHtml(token)}">`
                + `<img src="/static/images/ui/combat-icons/${icon}.svg" alt="">`
                + `<b>${amount}</b><span>${label}</span></span>`;
        });
        return `<span class="combat-feint-tip__cost-label">Стоимость</span>${chips.join('')}`;
    },

    renderFeintBadges(entry) {
        const badges = this.buildFeintBadges(entry);
        if (!badges.length) return '';
        const chips = badges.map((badge) => {
            const icon = `/static/images/ui/combat-icons/${badge.icon}.svg`;
            const value = badge.value ? `<b>${this.escapeHtml(String(badge.value))}</b>` : '';
            const label = this.escapeHtml(badge.label);
            return `<span class="combat-feint-tip__badge combat-feint-tip__badge--${this.escapeHtml(badge.kind)}">`
                + `<img src="${icon}" alt="">${value}<span>${label}</span></span>`;
        });
        return chips.join('');
    },

    renderFeintBadgesMini(entry) {
        const badges = this.buildFeintBadges(entry);
        if (!badges.length) return '';
        const chips = badges.slice(0, 3).map((badge) => {
            const icon = `/static/images/ui/combat-icons/${badge.icon}.svg`;
            const value = badge.value ? `<b>${this.escapeHtml(String(badge.value))}</b>` : '';
            const label = this.escapeHtml(badge.label);
            return `<span class="combat-feint-badge combat-feint-badge--${this.escapeHtml(badge.kind)}" title="${label}">`
                + `<img src="${icon}" alt="" aria-hidden="true">${value}</span>`;
        });
        return chips.join('');
    },

    buildFeintBadges(entry) {
        if (!entry) return [];
        const badges = [];
        const tags = new Set(Array.isArray(entry.applicability_tags) ? entry.applicability_tags : []);
        const damageBonus = entry.hit_damage_bonus_per_tier;
        if (damageBonus) {
            badges.push({ kind: 'damage', icon: 'token-hit', value: `+${damageBonus}`, label: 'Бонус урона' });
        }
        if (tags.has('ignore_miss')) {
            badges.push({ kind: 'tactical', icon: 'token-hit', label: 'Без промаха' });
        }
        if (tags.has('tempo')) {
            badges.push({ kind: 'tactical', icon: 'token-tempo', label: 'Темп' });
        }
        if (tags.has('punish')) {
            badges.push({ kind: 'tactical', icon: 'token-counter', label: 'Кара' });
        }
        if (tags.has('parry_window')) {
            badges.push({ kind: 'tactical', icon: 'token-parry', label: 'Парирование' });
        }
        const mutations = Array.isArray(entry.pipeline_mutations) ? entry.pipeline_mutations : [];
        const mutationIds = new Set(mutations.map((m) => (m && m.mutation_id) || ''));
        if (mutationIds.has('force_crit')) {
            badges.push({ kind: 'damage', icon: 'token-crit', label: 'Крит гарантирован' });
        }
        const effects = Array.isArray(entry.effects) ? entry.effects : [];
        for (const effect of effects) {
            if (!effect || typeof effect !== 'object') continue;
            const id = String(effect.id || '');
            const target = String(effect.target_actor || 'target');
            const params = effect.params || {};
            const duration = params.duration ? `${params.duration} р.` : '';
            const meta = this.feintEffectMeta(id, target);
            if (!meta) continue;
            badges.push({ kind: meta.kind, icon: meta.icon, value: duration, label: meta.label });
        }
        const prep = Array.isArray(entry.preparation_effects) ? entry.preparation_effects : [];
        for (const effect of prep) {
            if (!effect || typeof effect !== 'object') continue;
            const id = String(effect.id || '');
            const meta = this.feintEffectMeta(id, 'self');
            if (!meta) continue;
            badges.push({ kind: 'tactical', icon: meta.icon, label: `Подг. ${meta.label}` });
        }
        return badges;
    },

    feintEffectMeta(effectId, targetActor) {
        const control = { stun: 'Оглушение', slow: 'Замедление', immobilize: 'Обездв.', stagger: 'Сбив' };
        const debuff = {
            debuff_accuracy: 'Точность −',
            debuff_damage: 'Урон −',
            bleed: 'Кровотечение',
            poison: 'Яд',
            burn: 'Поджог',
            expose: 'Открытость',
            mark: 'Метка',
        };
        const damage = { bonus_damage: 'Бонус урона' };
        if (control[effectId]) return { kind: 'control', icon: 'stun', label: control[effectId] };
        if (debuff[effectId]) {
            const icon = effectId === 'bleed' ? 'bleeding' : effectId === 'poison' ? 'poison' : effectId === 'burn' ? 'burn' : 'token-pressure';
            const label = debuff[effectId];
            const prefix = targetActor === 'target' ? '' : '(вы) ';
            return { kind: 'debuff', icon, label: `${prefix}${label}` };
        }
        if (damage[effectId]) return { kind: 'damage', icon: 'token-hit', label: damage[effectId] };
        return null;
    },

    tokenIconFile(token) {
        const map = {
            tempo: 'token-tempo',
            hit: 'token-hit',
            crit: 'token-crit',
            dodge: 'token-dodge',
            parry: 'token-parry',
            block: 'token-block',
            pressure: 'token-pressure',
            blood: 'token-blood',
            gift: 'token-gift',
            counter: 'token-counter',
        };
        return map[token] || 'token';
    },

    escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, (ch) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[ch]));
    },

    formatAbilityTooltip(entry, taxonomy = 'humanoid') {
        if (!entry) return '';
        const title = this.getField(entry, 'title', taxonomy) || this.getField(entry, 'label', taxonomy);
        const description = this.getField(entry, 'description', taxonomy);
        const cost = this.formatAbilityCost(entry.cost);
        const target = entry.target_label || this.formatAbilityTarget(entry.target);
        const mechanics = Array.isArray(entry?.mechanics) ? entry.mechanics.filter(Boolean) : [];
        return [
            title,
            description,
            cost ? `Цена: ${cost}` : '',
            target ? `Цель: ${target}` : '',
            ...mechanics,
        ].filter(Boolean).join(' /' + '/ ');
    },

    formatAbilityCost(cost) {
        if (!cost || typeof cost !== 'object') return '';
        const parts = [];
        if (cost.energy) parts.push(`${cost.energy} EN`);
        if (cost.hp) parts.push(`${cost.hp} HP`);
        if (cost.gift_tokens) parts.push(`${cost.gift_tokens} дар`);
        Object.entries(cost.tokens || {}).forEach(([token, amount]) => {
            if (amount) parts.push(`${amount} ${this.formatCombatToken(token)}`);
        });
        return parts.join(' · ');
    },

    formatCombatToken(token) {
        const labels = {
            tempo: 'темп',
            hit: 'попадание',
            crit: 'крит',
            dodge: 'уклонение',
            parry: 'парирование',
            block: 'блок',
            counter: 'ответ',
            blood: 'кровь',
            gift: 'дар',
        };
        return labels[token] || token;
    },

    formatAbilityTarget(target) {
        const labels = {
            self: 'На себя',
            single_enemy: 'Один враг',
            all_enemies: 'Все враги',
            single_ally: 'Один союзник',
            all_allies: 'Все союзники',
            random_enemy: 'Случайный враг',
            lowest_hp_ally: 'Союзник с минимальным HP',
            lowest_hp_enemy: 'Враг с минимальным HP',
            cleave: 'Несколько врагов',
        };
        return labels[target] || target || '';
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
            const tooltipExtra = node.dataset.catalogTooltipExtra;
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
                let tooltip;
                if (tooltipField === 'ability') {
                    tooltip = this.formatAbilityTooltip(entry, taxonomy);
                } else if (tooltipField === 'feint') {
                    tooltip = this.formatFeintTooltip(entry, taxonomy);
                    node.dataset.tippyHtml = '1';
                } else {
                    tooltip = this.getField(entry, tooltipField, taxonomy);
                }
                const tooltipParts = [tooltip, tooltipExtra].filter(Boolean);
                if (tooltipParts.length) node.setAttribute('data-tippy-content', tooltipParts.join(' /' + '/ '));
            }
            if (node.dataset.catalogBadges === 'feint') {
                node.innerHTML = this.renderFeintBadgesMini(entry);
                node.classList.toggle('is-empty', !node.innerHTML);
            }
        });

        if (typeof tippy !== 'undefined') {
            const tooltipNodes = root.querySelectorAll('[data-tippy-content]');
            const tooltipContent = (node) => {
                const raw = node.getAttribute('data-tippy-content') || '';
                return raw.replace(/\\n/g, '\n').replace(/\s+\/\/\s+/g, '\n');
            };
            tooltipNodes.forEach((node) => {
                node.removeAttribute('title');
                if (node._tippy) {
                    node._tippy.setProps({ allowHTML: false });
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
                    maxWidth: 360,
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



(function () {
    const loadedScripts = new Set();
    const pendingScripts = new Map();

    function parseScripts(root) {
        if (!root || !root.dataset.gameScripts) {
            return [];
        }

        try {
            const scripts = JSON.parse(root.dataset.gameScripts);
            return Array.isArray(scripts) ? scripts.filter((src) => typeof src === "string" && src) : [];
        } catch (_error) {
            return [];
        }
    }

    function scriptKey(src) {
        try {
            return new URL(src, window.location.href).href;
        } catch (_error) {
            return src;
        }
    }

    function ensureScript(src) {
        const key = scriptKey(src);
        if (loadedScripts.has(key) || document.querySelector(`script[data-game-state-script="${key}"]`)) {
            loadedScripts.add(key);
            return Promise.resolve();
        }
        if (pendingScripts.has(key)) {
            return pendingScripts.get(key);
        }

        const promise = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = key;
            script.defer = true;
            script.dataset.gameStateScript = key;
            script.onload = () => {
                loadedScripts.add(key);
                pendingScripts.delete(key);
                resolve();
            };
            script.onerror = () => {
                pendingScripts.delete(key);
                reject(new Error(`GAME_STATE_SCRIPT_FAILED: ${key}`));
            };
            document.head.append(script);
        });
        pendingScripts.set(key, promise);
        return promise;
    }

    function rootsFromScope(scope) {
        const root = scope instanceof Element ? scope : document;
        const roots = [];
        if (root instanceof Element && root.matches("[data-game-state]")) {
            roots.push(root);
        }
        root.querySelectorAll("[data-game-state]").forEach((item) => roots.push(item));
        return roots;
    }

    function initRoot(root) {
        const state = root.dataset.gameState || "";
        const scripts = parseScripts(root);
        return Promise.all(scripts.map(ensureScript))
            .then(() => {
                const registry = window.GameStates || {};
                const handler = registry[state];
                if (handler && typeof handler.init === "function") {
                    handler.init(root);
                }
            })
            .catch((error) => {
                console.error(error);
            });
    }

    function init(scope) {
        return Promise.all(rootsFromScope(scope || document).map(initRoot));
    }

    window.GameStates = window.GameStates || {};
    window.GameStateLoader = {
        init,
        ensureScript,
    };

    document.addEventListener("DOMContentLoaded", () => init(document));
    document.addEventListener("htmx:load", (event) => init(event.target));
    document.addEventListener("htmx:afterSwap", (event) => init(event.target));
})();



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
    const worldDesktopPanelsDefaultOpen = () => {
        if (!["exploration", "rift"].includes(domain)) return false;
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
    const defaultRightPanelView = domain === "combats" ? "enemies" : "context";
    const normalizeLeftPanelView = (value) => {
        const view = typeof value === "string" ? value : "status";
        if (domain === "combats" && !["status", "allies"].includes(view)) {
            return "status";
        }
        return view;
    };
    const normalizeRightPanelView = (value) => {
        const view = typeof value === "string" ? value : defaultRightPanelView;
        if (domain === "combats" && !["enemies", "log"].includes(view)) {
            return "enemies";
        }
        if (noInventoryDomains.includes(domain) && view === "inventory") {
            return defaultRightPanelView;
        }
        return view;
    };
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
            return {
                leftOpen: saved.leftOpen,
                rightOpen: saved.rightOpen,
                leftPanelView: normalizeLeftPanelView(saved.leftPanelView),
                rightPanelView: normalizeRightPanelView(saved.rightPanelView),
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
                leftPanelView: normalizeLeftPanelView(state.leftPanelView),
                rightPanelView: normalizeRightPanelView(state.rightPanelView),
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
    const loadHudWindow = (name, defaults = {}) => {
        let geometry = { dragging: false, resizing: false, resizeEdge: "", open: false };
        try {
            const rawGeo = window.localStorage.getItem(hudStorageKey(name));
            if (rawGeo) {
                const parsed = JSON.parse(rawGeo);
                if (parsed.x !== undefined) geometry.x = parsed.x;
                if (parsed.y !== undefined) geometry.y = parsed.y;
                if (parsed.width !== undefined) geometry.width = parsed.width;
                if (parsed.height !== undefined) geometry.height = parsed.height;
            }
            const rawOpen = window.localStorage.getItem(hudOpenStorageKey(name));
            if (rawOpen) {
                geometry.open = JSON.parse(rawOpen).open;
            } else if (defaults.open !== undefined) {
                geometry.open = defaults.open;
            }
        } catch (_e) {}
        return Object.assign({}, defaults, geometry);
    };

    const savedPanelState = loadPanelState();
    const defaultPanelsOpen = worldDesktopPanelsDefaultOpen();
    const initialPanelState = savedPanelState || {
        leftOpen: !isDrawerViewport() && defaultPanelsOpen,
        rightOpen: !isDrawerViewport() && defaultPanelsOpen,
        leftPanelView: "status",
        rightPanelView: defaultRightPanelView,
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

    const chatWindowObj = loadHudWindow("chat", {
        open: false,
        width: 920,
        height: 540,
        x: Math.round((window.innerWidth - 920) / 2),
        y: Math.round((window.innerHeight - 540) / 2)
    });

    return {
        chatTab: "global",
        chatHeight: chatWindowObj.open ? chatWindowObj.height : 30,
        chatMinimized: !chatWindowObj.open,
        chatStep: chatWindowObj.open ? 2 : 0,
        chatClosed: !chatWindowObj.open,
        chatUnread: false,
        selectedAgentId: activeCharId,
        domain,
        agents: {
            [activeCharId]: initial.initialStatus || {},
        },
        leftPanelView: initialPanelState.leftPanelView,
        rightPanelView: initialPanelState.rightPanelView,
        panelStateUserEdited: savedPanelState !== null,
        windows: {
            chat: chatWindowObj
        },
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

        openChatOverlay() {
            this.chatClosed = false;
            this.chatUnread = false;
            if (this.windows.chat) {
                this.windows.chat.open = true;
                saveHudOpenState('chat', true);
            }
            if (typeof window.setChatStep === "function") {
                window.setChatStep(2);
                return;
            }
            this.chatStep = 2;
            this.chatMinimized = false;
        },

        closeChatOverlay() {
            this.chatClosed = true;
            if (this.windows.chat) {
                this.windows.chat.open = false;
                saveHudOpenState('chat', false);
            }
            if (typeof window.setChatStep === "function") {
                window.setChatStep(0);
                return;
            }
            this.chatStep = 0;
            this.chatMinimized = true;
        },

        toggleChatOverlay() {
            if (this.chatClosed) {
                this.openChatOverlay();
            } else {
                this.closeChatOverlay();
            }
        },

        toggleHudWindow(name) {
            if (name === 'chat') {
                this.toggleChatOverlay();
                return;
            }
            const hudWindow = this.windows[name];
            if (!hudWindow) return;
            hudWindow.open = !hudWindow.open;
            saveHudOpenState(name, hudWindow.open);
        },

        openUnavailableModal(detail = {}) {
            const modalRoot = document.getElementById("game-modal-root");
            if (!modalRoot) return;

            const copy = Object.assign({}, unavailableModalCopy[detail.kind] || {
                eyebrow: "SYSTEM",
                title: "Система будет доступна позже",
                body: "Этот функционал сейчас находится в разработке.",
            });
            if (detail.eyebrow) copy.eyebrow = detail.eyebrow;
            if (detail.title) copy.title = detail.title;
            if (detail.body) copy.body = detail.body;
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
            if (hudWindow.height !== null) {
                if (name === 'chat' && this.chatStep === 0) {

                } else {
                    parts.push(`height: ${hudWindow.height}px`);
                }
            }
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
    const chatRow   = document.querySelector('.game-chat-row') || document.querySelector('.game-chat-overlay');
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
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    const minStep = isMobile ? 0 : 1;
    const clamped = Math.max(minStep, Math.min(steps.length - 1, newStep));
    const height  = steps[clamped];
    const minMaxLabel = clamped === minStep ? 'MAX' : 'MIN';

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
        if (chatRow.classList.contains('game-chat-row')) {
            chatRow.style.height = height + 'px';
        } else {
            chatRow.style.removeProperty('height');
        }
    }

    if (window.Alpine) {
        const data = Alpine.$data(container);
        if (data) {
            data.chatStep      = clamped;
            data.chatHeight    = height;
            data.chatMinimized = (clamped === 0);
            if (data.windows && data.windows.chat) {
                if (clamped > 0) {
                    data.windows.chat.height = height;
                }
            }
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

    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    const minStep = isMobile ? 0 : 1;

    let newStep;
    if (dirOrTarget === 'min')      newStep = minStep;
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
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    const minStep = isMobile ? 0 : 1;
    _applyChatStep(currentStep === minStep ? 3 : minStep);
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
    } catch (e) {  }
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
