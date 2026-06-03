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
            const isHtmlNode = (node) => node.dataset.tippyHtml === '1';
            const tooltipContent = (node) => {
                const raw = node.getAttribute('data-tippy-content') || '';
                if (isHtmlNode(node)) return raw;
                return raw.replace(/\\n/g, '\n').replace(/\s+\/\/\s+/g, '\n');
            };
            tooltipNodes.forEach((node) => {
                node.removeAttribute('title');
                if (node._tippy) {
                    node._tippy.setProps({ allowHTML: isHtmlNode(node) });
                    node._tippy.setContent(tooltipContent(node));
                }
            });
            Array.from(tooltipNodes).filter((node) => !node._tippy).forEach((node) => {
                tippy(node, {
                    allowHTML: isHtmlNode(node),
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
