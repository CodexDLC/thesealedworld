(function () {
    const RIFT_ENCOUNTER_REVEAL_MS = 760;
    const RIFT_ENCOUNTER_READY_DELAY_MS = 140;

    function createRiftMapStore() {
        const version = "v3";
        const edgeKey = (edge) => [
            edge.from_node_id || "",
            edge.to_node_id || "",
            edge.absolute_direction || "",
        ].join(":");
        const storagePrefix = (riftInstanceId) => `tbmmorpg:rift:map:${riftInstanceId}:`;
        const storageKey = (riftInstanceId, mapScopeId) => {
            const scope = mapScopeId || "default";
            return `${storagePrefix(riftInstanceId)}${scope}:${version}`;
        };
        const legacyStorageKey = (riftInstanceId) => `tbmmorpg:rift:map:${riftInstanceId}:v1`;

        const read = (riftInstanceId, mapScopeId) => {
            try {
                const raw = window.localStorage.getItem(storageKey(riftInstanceId, mapScopeId))
                    || window.sessionStorage.getItem(storageKey(riftInstanceId, mapScopeId));
                if (!raw) return null;
                return JSON.parse(raw);
            } catch (_error) {
                return null;
            }
        };

        const write = (riftInstanceId, mapScopeId, state) => {
            try {
                window.localStorage.setItem(storageKey(riftInstanceId, mapScopeId), JSON.stringify(state));
            } catch (_error) {
                try {
                    window.sessionStorage.setItem(storageKey(riftInstanceId, mapScopeId), JSON.stringify(state));
                } catch (_fallbackError) {
                    return;
                }
            }
        };

        const merge = ({ riftInstanceId, mapScopeId, mapView }) => {
            if (!riftInstanceId || !mapScopeId || !mapView) return null;
            const previous = read(riftInstanceId, mapScopeId) || {
                rift_instance_id: riftInstanceId,
                map_scope_id: mapScopeId,
                nodes: {},
                edges: {},
            };
            const nodes = Object.assign({}, previous.nodes || {});
            const edges = Object.assign({}, previous.edges || {});

            (mapView.visible_nodes || []).forEach((node) => {
                if (!node || !node.node_id) return;
                nodes[node.node_id] = Object.assign({}, nodes[node.node_id] || {}, node);
            });
            if (mapView.center_node_id) {
                Object.keys(nodes).forEach((nodeId) => {
                    if (nodeId !== mapView.center_node_id && nodes[nodeId].state === "current") {
                        nodes[nodeId] = Object.assign({}, nodes[nodeId], {
                            state: "open",
                            visited: true,
                        });
                    }
                });
            }
            (mapView.visible_edges || []).forEach((edge) => {
                const key = edgeKey(edge || {});
                if (!key.trim()) return;
                edges[key] = Object.assign({}, edges[key] || {}, edge);
            });

            const merged = {
                rift_instance_id: riftInstanceId,
                map_scope_id: mapScopeId,
                center_node_id: mapView.center_node_id || previous.center_node_id || null,
                current_coord: mapView.current_coord || previous.current_coord || null,
                heading: mapView.heading || previous.heading || null,
                nodes,
                edges,
            };
            write(riftInstanceId, mapScopeId, merged);
            return merged;
        };

        const removeStoredMaps = (storage, riftInstanceId) => {
            const prefix = storagePrefix(riftInstanceId);
            const keys = [];
            for (let index = 0; index < storage.length; index += 1) {
                const key = storage.key(index);
                if (key && (key.startsWith(prefix) || key === legacyStorageKey(riftInstanceId))) {
                    keys.push(key);
                }
            }
            keys.forEach((key) => storage.removeItem(key));
        };

        const reset = (riftInstanceId, mapScopeId) => {
            if (!riftInstanceId) return;
            try {
                if (mapScopeId) {
                    window.sessionStorage.removeItem(storageKey(riftInstanceId, mapScopeId));
                } else {
                    removeStoredMaps(window.sessionStorage, riftInstanceId);
                }
            } catch (_error) {
            }
            try {
                if (mapScopeId) {
                    window.localStorage.removeItem(storageKey(riftInstanceId, mapScopeId));
                } else {
                    removeStoredMaps(window.localStorage, riftInstanceId);
                }
            } catch (_error) {
            }
        };

        return {
            merge,
            read,
            reset,
            storageKey,
        };
    }

    function createRiftMapPan(store) {
        function sleep(ms) {
            return new Promise((resolve) => {
                window.setTimeout(resolve, Math.max(0, ms));
            });
        }

        function numberFromStyle(element, name) {
            const value = getComputedStyle(element).getPropertyValue(name).trim();
            const parsed = Number.parseFloat(value);
            return Number.isFinite(parsed) ? parsed : 0;
        }

        function parseMapView(root) {
            if (!root || !root.dataset.riftMapView) {
                return null;
            }

            try {
                return JSON.parse(root.dataset.riftMapView);
            } catch (_error) {
                return null;
            }
        }

        function stateLabel(node, isCurrent) {
            if (isCurrent) return "текущая";
            if (node.visited) return "посещена";
            if (node.state === "open") return "открыта";
            if (node.state === "blocked_temporary") return "временный блок";
            if (node.state === "void") return "пустота";
            if (node.state === "unknown") return "неизвестно";
            return node.state || "неизвестно";
        }

        function nodePosition(node, currentCoord) {
            if (!node || !node.coord || !currentCoord) {
                return { x: 0, y: 0 };
            }

            return {
                x: node.coord.x - currentCoord.x,
                y: node.coord.y - currentCoord.y,
            };
        }

        function edgeDirection(fromPosition, toPosition) {
            const deltaX = toPosition.x - fromPosition.x;
            const deltaY = toPosition.y - fromPosition.y;
            if (deltaX === 1 && deltaY === 0) return "east";
            if (deltaX === -1 && deltaY === 0) return "west";
            if (deltaX === 0 && deltaY === 1) return "south";
            if (deltaX === 0 && deltaY === -1) return "north";
            return null;
        }

        function shouldRenderEdge(edge) {
            if (!edge || !edge.to_node_id) return false;
            return edge.state === "open" || edge.state === "blocked_temporary";
        }

        function shouldRenderNode(node, centerNodeId) {
            if (!node || !node.node_id) return false;
            if (node.node_id === centerNodeId || node.state === "current") return true;
            return node.state === "open" || node.state === "blocked_temporary";
        }

        function headingRotation(heading) {
            if (heading === "east") return "90deg";
            if (heading === "south") return "180deg";
            if (heading === "west") return "270deg";
            return "0deg";
        }

        function createEdge(edge, direction, position) {
            const element = document.createElement("span");
            element.className = `rift-map-edge rift-map-edge--${direction} is-state-${edge.state || "unknown"}`;
            element.dataset.riftDirection = edge.absolute_direction || "";
            element.dataset.riftRelativeDirection = edge.relative_direction || "";
            element.dataset.riftTarget = edge.to_node_id || "";
            element.setAttribute("aria-hidden", "true");
            element.style.setProperty("--rift-edge-x", `${position.x}`);
            element.style.setProperty("--rift-edge-y", `${position.y}`);
            return element;
        }

        function createNode(node, position, centerNodeId, heading) {
            const isCurrent = node.node_id === centerNodeId;
            const visualState = isCurrent ? "current" : (node.state === "current" ? "open" : (node.state || "unknown"));
            const element = document.createElement("article");
            element.className = [
                "rift-map-node",
                `is-state-${visualState}`,
                isCurrent ? "is-current" : "",
                node.visited ? "is-visited" : "",
            ].filter(Boolean).join(" ");
            element.dataset.riftNodeId = node.node_id || "";
            element.dataset.tippyContent = [node.title || "NO_DATA", stateLabel(node, isCurrent)].join(" - ");
            element.dataset.tippyTheme = "game-hint";
            element.setAttribute("aria-label", node.title || "NO_DATA");
            element.setAttribute("tabindex", "0");
            element.style.setProperty("--rift-node-dx", `${position.x}`);
            element.style.setProperty("--rift-node-dy", `${position.y}`);
            if (isCurrent) {
                element.style.setProperty("--rift-current-marker-rotation", headingRotation(heading));
            }

            const marker = document.createElement("span");
            marker.setAttribute("aria-hidden", "true");
            const title = document.createElement("strong");
            title.textContent = node.title || "NO_DATA";
            element.append(marker, title);
            return element;
        }

        function initialiseTooltips(root) {
            if (typeof tippy === "undefined") {
                return;
            }

            const nodes = Array.from(root.querySelectorAll("[data-tippy-content]"));
            nodes.forEach((node) => {
                if (node._tippy) {
                    node._tippy.setContent(node.getAttribute("data-tippy-content") || "");
                    return;
                }
                tippy(node, {
                    content: node.getAttribute("data-tippy-content") || "",
                    delay: [120, 0],
                    maxWidth: 260,
                    placement: "top",
                    theme: node.getAttribute("data-tippy-theme") || "game-hint",
                });
            });
        }

        function refreshTooltips(root) {
            if (typeof window.initGameTooltips === "function") {
                window.initGameTooltips(root || document);
                return;
            }
            initialiseTooltips(root || document);
        }

        function refreshCatalog(root) {
            if (!window.GameCatalogCache || typeof window.GameCatalogCache.init !== "function") {
                return;
            }
            window.GameCatalogCache.init().then(() => {
                if (typeof window.GameCatalogCache.resolveDom === "function") {
                    window.GameCatalogCache.resolveDom(root || document);
                }
            }).catch((error) => {
                console.error(error);
            });
        }

        function refreshCharacterStatus() {
            if (window.CharacterStatus && typeof window.CharacterStatus.refresh === "function") {
                window.CharacterStatus.refresh();
            }
        }

        function parseNumber(value, fallback = 0) {
            const parsed = Number.parseInt(value || "", 10);
            return Number.isFinite(parsed) ? parsed : fallback;
        }

        function parseFloatNumber(value, fallback = 0) {
            const parsed = Number.parseFloat(value || "");
            return Number.isFinite(parsed) ? parsed : fallback;
        }

        function parseJsonList(value) {
            try {
                const parsed = JSON.parse(value || "[]");
                return Array.isArray(parsed) ? parsed : [];
            } catch (_error) {
                return [];
            }
        }

        function travelFromButton(button) {
            return {
                kind: button.dataset.riftTravelKind || "unknown",
                durationMs: parseNumber(button.dataset.riftTravelDuration, 0),
                tickIntervalMs: parseNumber(button.dataset.riftTravelTickInterval, 0),
                eventCheckCount: parseNumber(button.dataset.riftTravelCheckCount, 0),
                eventScope: button.dataset.riftTravelEventScope || "",
                possibleEvents: parseJsonList(button.dataset.riftTravelPossibleEvents),
                canTriggerEvent: button.dataset.riftTravelCanTriggerEvent === "true",
                eventChance: parseFloatNumber(button.dataset.riftTravelEventChance, 0),
            };
        }

        function travelFromResponse(rawTravel, fallbackTravel) {
            const travel = rawTravel || {};
            return {
                travelId: travel.travel_id || "",
                status: travel.status || "moving",
                kind: travel.kind || fallbackTravel.kind || "unknown",
                durationMs: parseNumber(travel.duration_ms, fallbackTravel.durationMs || 0),
                tickIntervalMs: parseNumber(travel.tick_interval_ms, fallbackTravel.tickIntervalMs || 0),
                checksDone: parseNumber(travel.checks_done, 0),
                checksTotal: parseNumber(travel.checks_total, fallbackTravel.eventCheckCount || 0),
                remainingMs: parseNumber(travel.remaining_ms, fallbackTravel.durationMs || 0),
                possibleEvents: Array.isArray(travel.possible_events) ? travel.possible_events : fallbackTravel.possibleEvents,
                canTriggerEvent: (Array.isArray(travel.possible_events) ? travel.possible_events : fallbackTravel.possibleEvents).includes("combat"),
                eventScope: travel.event_scope || fallbackTravel.eventScope || "transition",
            };
        }

        function formatTime(ms) {
            return `${Math.max(0, ms / 1000).toFixed(1)}s`;
        }

        function renderTravelTicks(container, travel) {
            container.replaceChildren();
            const fallbackTotal = travel.durationMs > 0 && travel.tickIntervalMs > 0
                ? Math.max(1, Math.floor(travel.durationMs / travel.tickIntervalMs))
                : 0;
            const total = travel.checksTotal || travel.eventCheckCount || fallbackTotal;
            if (!total || total < 1) {
                return;
            }

            const fragment = document.createDocumentFragment();
            for (let index = 1; index <= total; index += 1) {
                const tick = document.createElement("span");
                const tickMs = travel.tickIntervalMs > 0
                    ? travel.tickIntervalMs * index
                    : (travel.durationMs / total) * index;
                tick.style.left = `${Math.min(100, (tickMs / travel.durationMs) * 100)}%`;
                if (travel.checksDone && index <= travel.checksDone) {
                    tick.classList.add("is-done");
                }
                fragment.append(tick);
            }
            container.append(fragment);
        }

        function setupTravelOverlay(scope, button, travel) {
            const overlay = scope.querySelector("[data-rift-travel-overlay]");
            if (!overlay) {
                return null;
            }

            const label = overlay.querySelector("[data-rift-travel-label]");
            const time = overlay.querySelector("[data-rift-travel-time]");
            const fill = overlay.querySelector("[data-rift-travel-fill]");
            const ticks = overlay.querySelector("[data-rift-travel-ticks]");
            const buttonLabel = button.querySelector("strong");

            overlay.hidden = false;
            overlay.classList.add("is-active");
            overlay.dataset.riftTravelKind = travel.kind;
            overlay.dataset.riftTravelScope = travel.eventScope;
            overlay.dataset.riftTravelCombat = travel.canTriggerEvent && travel.possibleEvents.includes("combat") ? "true" : "false";
            if (label) label.textContent = buttonLabel ? buttonLabel.textContent.trim() : "";
            if (time) time.textContent = formatTime(travel.remainingMs || travel.durationMs);
            if (fill) fill.style.transform = `scaleX(${travel.durationMs ? 1 - ((travel.remainingMs || travel.durationMs) / travel.durationMs) : 0})`;
            if (ticks) renderTravelTicks(ticks, travel);
            return overlay;
        }

        function hideTravelOverlay(riftRoot) {
            const overlay = riftRoot ? riftRoot.querySelector("[data-rift-travel-overlay]") : null;
            if (!overlay) return;
            overlay.hidden = true;
            overlay.classList.remove("is-active", "is-interrupted");
            delete overlay.dataset.riftTravelState;
            overlay.style.removeProperty("--rift-travel-progress");
        }

        function animateTravelSegment(overlay, travel) {
            if (!overlay || travel.status !== "moving") {
                return Promise.resolve();
            }

            const time = overlay.querySelector("[data-rift-travel-time]");
            const fill = overlay.querySelector("[data-rift-travel-fill]");
            const segmentMs = Math.max(0, Math.min(travel.tickIntervalMs || travel.remainingMs, travel.remainingMs));
            const startRemaining = travel.remainingMs;
            const startedAt = performance.now();
            return new Promise((resolve) => {
                function step(now) {
                    const elapsed = Math.min(segmentMs, now - startedAt);
                    const remaining = Math.max(0, startRemaining - elapsed);
                    const progress = travel.durationMs > 0 ? 1 - (remaining / travel.durationMs) : 1;
                    overlay.style.setProperty("--rift-travel-progress", `${progress}`);
                    if (fill) fill.style.transform = `scaleX(${progress})`;
                    if (time) time.textContent = formatTime(remaining);

                    if (elapsed >= segmentMs) {
                        resolve();
                        return;
                    }

                    window.requestAnimationFrame(step);
                }

                window.requestAnimationFrame(step);
            });
        }

        function postForm(url, data, options = {}) {
            const body = new URLSearchParams();
            Object.entries(data).forEach(([key, value]) => {
                if (value !== undefined && value !== null && value !== "") {
                    body.set(key, value);
                }
            });
            return fetch(url, {
                method: "POST",
                headers: {
                    "Accept": options.accept || "application/json",
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                },
                body,
            }).then((response) => {
                if (!response.ok) {
                    throw new Error(`RIFT_TRAVEL_REQUEST_FAILED:${response.status}`);
                }
                return options.raw ? response : response.json();
            });
        }

        function replaceSessionRoot(html) {
            if (!html) return;
            const currentRoot = document.getElementById("game-session-root");
            if (!currentRoot) return;

            const template = document.createElement("template");
            template.innerHTML = html.trim();
            const nextRoot = template.content.firstElementChild;
            if (!nextRoot) return;

            currentRoot.replaceWith(nextRoot);
            if (window.htmx && typeof window.htmx.process === "function") {
                window.htmx.process(nextRoot);
            }
            if (window.GameStateLoader && typeof window.GameStateLoader.init === "function") {
                window.GameStateLoader.init(nextRoot);
            }
            refreshCatalog(nextRoot);
            refreshTooltips(nextRoot);
            refreshCharacterStatus();
        }

        async function enterCombatFromPrompt(riftRoot, button) {
            const charId = riftRoot.dataset.riftCharId || "";
            const combatId = button.dataset.riftCombatId || "";
            const enterUrl = riftRoot.dataset.riftCombatEnterUrl || "/game/rift/combat/enter";
            if (!charId || charId === "0" || !combatId) {
                return null;
            }
            const response = await postForm(enterUrl, {
                char_id: charId,
                combat_id: combatId,
            }, { accept: "text/html", raw: true });
            replaceSessionRoot(await response.text());
            return response;
        }

        async function resolveCombatPlaceholder(riftRoot, button) {
            const riftInstanceId = riftRoot.dataset.riftInstanceId || "";
            const charId = riftRoot.dataset.riftCharId || "";
            const travelId = button.dataset.riftTravelId || "";
            const resolveUrl = riftRoot.dataset.riftActionUrl || "/game/rift/action";
            if (!riftInstanceId || !travelId) {
                throw new Error("RIFT_COMBAT_RESOLVE_MISSING_CONTEXT");
            }

            const response = await postForm(resolveUrl, {
                rift_instance_id: riftInstanceId,
                char_id: charId,
                action_type: "resolve_transition_combat",
                travel_id: travelId,
                result: "victory",
            });
            if (response.html) {
                replaceSessionRoot(response.html);
            }
            return response;
        }

        function formatCombatPromptSource(source) {
            if (source === "rift_transition") {
                return "Событие перехода";
            }
            return "";
        }

        function createEnemyRosterButton(enemy, index) {
            const card = document.createElement("button");
            card.type = "button";
            card.className = `mobile-encounter-roster-target${index === 0 ? " is-active" : ""}`;
            card.dataset.riftEnemyIndex = String(index);
            card.setAttribute("aria-pressed", index === 0 ? "true" : "false");
            const title = document.createElement("strong");
            title.textContent = enemy.name || "???";
            const meta = document.createElement("small");
            meta.textContent = "???";
            card.append(title, meta);
            return card;
        }

        function isFamilyFallbackImage(url) {
            return String(url || "").includes("/static/images/monsters/families/");
        }

        function uniqueImageCandidates(values) {
            return values.filter((value, index, items) => value && items.indexOf(value) === index);
        }

        function enemyImageCandidates(enemy) {
            const visual = enemy && typeof enemy.visual === "object" && enemy.visual !== null ? enemy.visual : {};
            const generatedCandidates = [
                enemy.image,
                !isFamilyFallbackImage(visual.image_url) ? visual.image_url : null,
                visual.generated_image_url,
            ];
            const fallbackCandidates = [
                visual.placeholder_image_url,
                isFamilyFallbackImage(visual.image_url) ? visual.image_url : null,
            ];
            return uniqueImageCandidates([...generatedCandidates, ...fallbackCandidates]);
        }

        function appendEnemyArtFallback(art, enemy, promptData) {
            const artFallback = document.createElement("span");
            artFallback.textContent = enemy.name || promptData.title || "UNKNOWN";
            art.append(artFallback);
        }

        function appendEnemyImage(art, images, enemy, promptData) {
            if (!images.length) {
                appendEnemyArtFallback(art, enemy, promptData);
                return;
            }
            const image = document.createElement("img");
            image.className = "mobile-encounter-target-image";
            image.alt = enemy.name || promptData.title || "UNKNOWN";
            let index = 0;
            if (isFamilyFallbackImage(images[index])) {
                image.classList.add("is-family-fallback");
            }
            image.src = images[index];
            image.addEventListener("error", () => {
                index += 1;
                if (index < images.length) {
                    image.classList.toggle("is-family-fallback", isFamilyFallbackImage(images[index]));
                    image.src = images[index];
                    return;
                }
                image.remove();
                appendEnemyArtFallback(art, enemy, promptData);
            });
            art.append(image);
        }

        function enemyIntel(enemy) {
            return enemy && typeof enemy.intel === "object" && enemy.intel !== null ? enemy.intel : {};
        }

        function nestedLabel(source, key) {
            const value = source && typeof source === "object" ? source[key] : null;
            return value && typeof value === "object" && value.label ? String(value.label) : null;
        }

        function appendEnemyStat(stats, label, value) {
            const item = document.createElement("div");
            const statLabel = document.createElement("span");
            statLabel.textContent = label;
            const statValue = document.createElement("strong");
            statValue.textContent = value || "???";
            item.append(statLabel, statValue);
            stats.append(item);
        }

        function createEnemyDetail(enemy, promptData) {
            const detail = document.createElement("div");
            detail.className = "mobile-encounter-target-view";
            const intel = enemyIntel(enemy);
            const vitals = intel && typeof intel.vitals === "object" && intel.vitals !== null ? intel.vitals : {};
            const main = document.createElement("div");
            main.className = "mobile-encounter-target-main";
            const art = document.createElement("div");
            art.className = "mobile-encounter-target-art";
            appendEnemyImage(art, enemyImageCandidates(enemy), enemy, promptData);

            const copy = document.createElement("div");
            copy.className = "mobile-encounter-target-copy";
            const title = document.createElement("div");
            title.className = "mobile-encounter-target-title";
            const titleName = document.createElement("strong");
            titleName.textContent = enemy.name || "UNKNOWN TARGET";
            const tier = document.createElement("span");
            const tierValue = enemy.member_tier ?? enemy.tier ?? enemy.level ?? "?";
            tier.textContent = `TIER ${tierValue}`;
            title.append(titleName, tier);
            const tags = document.createElement("div");
            tags.className = "mobile-encounter-target-tags";
            const status = document.createElement("span");
            status.textContent = promptData.status || "DETECTED";
            const role = document.createElement("span");
            role.textContent = enemy.role || enemy.variant_key || "HOSTILE";
            tags.append(status, role);
            const description = document.createElement("p");
            description.textContent = enemy.description || promptData.description || "NO_DATA";
            copy.append(title, tags, description);

            main.append(art, copy);
            const stats = document.createElement("div");
            stats.className = "mobile-encounter-target-stats";
            appendEnemyStat(
                stats,
                "HEALTH",
                nestedLabel(vitals, "hp") || (enemy.hp_percent === null || enemy.hp_percent === undefined ? null : `${enemy.hp_percent}%`),
            );
            appendEnemyStat(stats, "ENERGY", nestedLabel(vitals, "energy"));
            appendEnemyStat(stats, "CONC", nestedLabel(vitals, "concentration"));
            appendEnemyStat(stats, "DANGER", intel.danger_band || null);
            detail.append(main, stats);
            return detail;
        }

        function selectEnemyDetail(enemiesContainer, detailContainer, promptEnemies, promptData, index, position) {
            const nextIndex = Math.max(0, Math.min(promptEnemies.length - 1, index));
            enemiesContainer.querySelectorAll("[data-rift-enemy-index]").forEach((button) => {
                const isActive = Number.parseInt(button.dataset.riftEnemyIndex || "0", 10) === nextIndex;
                button.classList.toggle("is-active", isActive);
                button.setAttribute("aria-pressed", isActive ? "true" : "false");
            });
            if (position) {
                position.textContent = `${nextIndex + 1} / ${promptEnemies.length}`;
            }
            detailContainer.replaceChildren(createEnemyDetail(promptEnemies[nextIndex] || {}, promptData));
        }

        function renderCombatPrompt(riftRoot, promptData) {
            const prompt = riftRoot ? riftRoot.querySelector("[data-rift-combat-prompt]") : null;
            const actionPanel = riftRoot ? riftRoot.querySelector("[data-rift-combat-actions]") : null;
            if (!prompt || !actionPanel || !promptData) return;

            const source = prompt.querySelector("[data-rift-combat-prompt-source]");
            const title = prompt.querySelector("[data-rift-combat-prompt-title]");
            const description = prompt.querySelector("[data-rift-combat-prompt-description]");
            const count = prompt.querySelector("[data-rift-combat-prompt-count]");
            const position = prompt.querySelector("[data-rift-combat-prompt-position]");
            const previous = prompt.querySelector("[data-rift-enemy-prev]");
            const next = prompt.querySelector("[data-rift-enemy-next]");
            const promptEnemies = Array.isArray(promptData.enemies) && promptData.enemies.length
                ? promptData.enemies
                : [{}];
            if (source) {
                source.textContent = formatCombatPromptSource(promptData.source) || "ENCOUNTER DETECTED";
                source.hidden = false;
            }
            if (title) title.textContent = promptData.title || "";
            if (description) description.textContent = promptData.description || "";
            if (count) count.textContent = String(promptEnemies.length);
            if (position) position.textContent = `1 / ${promptEnemies.length}`;

            const actionSource = actionPanel.querySelector("[data-rift-combat-actions-source]");
            const actionTitle = actionPanel.querySelector("[data-rift-combat-actions-title]");
            const enemies = prompt.querySelector("[data-rift-combat-enemies]");
            const detail = prompt.querySelector("[data-rift-combat-detail]");
            const actionGrid = actionPanel.querySelector("[data-rift-combat-action-grid]");
            if (actionSource) actionSource.textContent = formatCombatPromptSource(promptData.source);
            if (actionTitle) actionTitle.textContent = promptData.title || "";
            if (enemies) {
                const enemyFragment = document.createDocumentFragment();
                promptEnemies.forEach((enemy, index) => {
                    enemyFragment.append(createEnemyRosterButton(enemy || {}, index));
                });
                enemies.replaceChildren(enemyFragment);
            }
            if (detail) {
                detail.replaceChildren(createEnemyDetail(promptEnemies[0] || {}, promptData));
            }
            if (enemies && detail) {
                enemies.onclick = (event) => {
                    if (!(event.target instanceof Element)) return;
                    const button = event.target.closest("[data-rift-enemy-index]");
                    if (!button || !enemies.contains(button)) return;
                    event.preventDefault();
                    selectEnemyDetail(
                        enemies,
                        detail,
                        promptEnemies,
                        promptData,
                        Number.parseInt(button.dataset.riftEnemyIndex || "0", 10),
                        position,
                    );
                };
            }
            if (previous && enemies && detail) {
                previous.onclick = () => {
                    const current = Number.parseInt(
                        enemies.querySelector(".is-active")?.dataset.riftEnemyIndex || "0",
                        10,
                    );
                    selectEnemyDetail(enemies, detail, promptEnemies, promptData, current - 1, position);
                };
            }
            if (next && enemies && detail) {
                next.onclick = () => {
                    const current = Number.parseInt(
                        enemies.querySelector(".is-active")?.dataset.riftEnemyIndex || "0",
                        10,
                    );
                    selectEnemyDetail(enemies, detail, promptEnemies, promptData, current + 1, position);
                };
            }
            if (actionGrid) {
                const fragment = document.createDocumentFragment();
                (promptData.actions || []).forEach((action) => {
                    const button = document.createElement("button");
                    button.type = "button";
                    button.className = [
                        "game-action-button",
                        "mobile-encounter-action",
                        action.style === "danger" || action.action === "attack"
                            ? "mobile-encounter-action--fight"
                            : "mobile-encounter-action--escape",
                        `is-style-${action.style || "danger"}`,
                    ].join(" ");
                    button.dataset.riftCombatAction = action.action || "attack";
                    button.dataset.riftTravelId = promptData.metadata && promptData.metadata.travel_id ? promptData.metadata.travel_id : "";
                    button.dataset.riftCombatId = (
                        promptData.metadata
                        && promptData.metadata.combat
                        && promptData.metadata.combat.combat_id
                    ) ? promptData.metadata.combat.combat_id : "";
                    button.dataset.riftCombatMode = button.dataset.riftCombatId ? "combat_session" : "dev_placeholder";
                    button.disabled = !action.is_active;
                    const label = document.createElement("strong");
                    label.textContent = action.label || "NO_DATA";
                    const meta = document.createElement("span");
                    meta.textContent = action.action === "attack" ? "combat transition" : "encounter decision";
                    button.append(label, meta);
                    fragment.append(button);
                });
                actionGrid.replaceChildren(fragment);
            }

            prompt.hidden = false;
            actionPanel.hidden = true;
            if (riftRoot) {
                riftRoot.classList.add("has-combat-prompt");
            }
        }

        async function revealCombatPrompt(riftRoot, promptData) {
            if (!riftRoot || !promptData) return;

            renderCombatPrompt(riftRoot, promptData);
            const overlay = riftRoot.querySelector("[data-rift-travel-overlay]");
            const nodeCopy = riftRoot.querySelector(".rift-node-copy");
            const actionPanel = riftRoot.querySelector("[data-rift-combat-actions]");
            const time = overlay ? overlay.querySelector("[data-rift-travel-time]") : null;

            if (nodeCopy) nodeCopy.hidden = false;
            if (actionPanel) actionPanel.hidden = true;
            if (overlay) {
                overlay.hidden = false;
                overlay.classList.add("is-active", "is-interrupted");
                overlay.dataset.riftTravelState = "interrupted";
                if (time) time.textContent = "CONTACT";
            }

            riftRoot.classList.remove("is-encounter-ready");
            riftRoot.classList.add("has-combat-prompt", "is-encounter-revealing");
            riftRoot.dataset.riftPhase = "encounter-reveal";
            await sleep(RIFT_ENCOUNTER_REVEAL_MS);

            hideTravelOverlay(riftRoot);
            if (nodeCopy) nodeCopy.hidden = true;
            riftRoot.classList.remove("is-encounter-revealing");
            riftRoot.classList.add("is-encounter-ready");
            riftRoot.dataset.riftPhase = "encounter-ready";
            await sleep(RIFT_ENCOUNTER_READY_DELAY_MS);

            if (actionPanel) actionPanel.hidden = false;
        }

        function forceEventFromLocation() {
            const value = new URLSearchParams(window.location.search).get("rift_force_event");
            return value === "combat" || value === "none" ? value : "";
        }

        async function runTravelFlow(riftRoot, button, fallbackTravel) {
            const riftInstanceId = riftRoot.dataset.riftInstanceId || "";
            const charId = riftRoot.dataset.riftCharId || "";
            const targetNodeId = button.dataset.riftTarget || "";
            const startUrl = riftRoot.dataset.riftTravelStartUrl || "/game/rift/travel/start";
            const tickUrl = riftRoot.dataset.riftTravelTickUrl || "/game/rift/travel/tick";
            let response = await postForm(startUrl, {
                rift_instance_id: riftInstanceId,
                char_id: charId,
                target_node_id: targetNodeId,
            });
            let travel = travelFromResponse(response.travel, fallbackTravel);
            const overlay = setupTravelOverlay(riftRoot, button, travel);

            if (response.combat_prompt) {
                await revealCombatPrompt(riftRoot, response.combat_prompt);
                return;
            }
            if (travel.status === "completed" && response.html) {
                replaceSessionRoot(response.html);
                return;
            }

            while (travel.status === "moving") {
                await animateTravelSegment(overlay, travel);
                response = await postForm(tickUrl, {
                    rift_instance_id: riftInstanceId,
                    char_id: charId,
                    travel_id: travel.travelId,
                    force_event: forceEventFromLocation(),
                });
                travel = travelFromResponse(response.travel, fallbackTravel);
                setupTravelOverlay(riftRoot, button, travel);

                if (response.combat_prompt) {
                    await revealCombatPrompt(riftRoot, response.combat_prompt);
                    return;
                }
                if (travel.status === "completed" && response.html) {
                    replaceSessionRoot(response.html);
                    return;
                }
            }
        }

        function bindTravelButtons(root) {
            const scope = root instanceof Element ? root : document;
            const riftRoot = scope.matches && scope.matches("[data-rift-instance-id]")
                ? scope
                : scope.querySelector("[data-rift-instance-id]");
            if (!riftRoot || riftRoot.dataset.riftTravelReady === "1") {
                return;
            }

            riftRoot.dataset.riftTravelReady = "1";
            riftRoot.addEventListener("click", (event) => {
                if (!(event.target instanceof Element)) {
                    return;
                }

                const blockedButton = event.target.closest("[data-rift-blocker-feedback]");
                if (blockedButton && riftRoot.contains(blockedButton)) {
                    event.preventDefault();
                    event.stopPropagation();
                    window.dispatchEvent(new CustomEvent("game-modal-open", {
                        detail: {
                            eyebrow: "RIFT",
                            title: "Проход закрыт",
                            body: blockedButton.dataset.riftBlockerFeedback || "Сейчас пройти нельзя.",
                        },
                    }));
                    return;
                }

                const button = event.target.closest("[data-rift-action='move'][data-rift-travel-duration]");
                if (!button || !riftRoot.contains(button) || button.disabled) {
                    return;
                }

                const travel = travelFromButton(button);
                if (button.dataset.riftTravelRunning === "1") {
                    event.preventDefault();
                    event.stopPropagation();
                    return;
                }
                if (travel.durationMs <= 0) {
                    return;
                }

                event.preventDefault();
                event.stopPropagation();
                button.dataset.riftTravelRunning = "1";
                button.classList.add("is-travel-running");

                runTravelFlow(riftRoot, button, travel).catch((error) => {
                    console.error(error);
                }).finally(() => {
                    button.classList.remove("is-travel-running");
                    delete button.dataset.riftTravelRunning;
                });
            }, true);
        }

        function bindCombatPromptActions(root) {
            const scope = root instanceof Element ? root : document;
            const riftRoot = scope.matches && scope.matches("[data-rift-instance-id]")
                ? scope
                : scope.querySelector("[data-rift-instance-id]");
            if (!riftRoot || riftRoot.dataset.riftCombatActionsReady === "1") {
                return;
            }
            riftRoot.dataset.riftCombatActionsReady = "1";

            riftRoot.addEventListener("click", (event) => {
                if (!(event.target instanceof Element)) return;
                const button = event.target.closest("[data-rift-combat-action='attack']");
                if (!button || button.disabled) return;

                event.preventDefault();
                button.disabled = true;
                button.classList.add("is-pending");
                button.textContent = button.dataset.riftCombatMode === "combat_session" ? "ВХОД В БОЙ" : "БОЙ ЗАВЕРШАЕТСЯ";
                const transition = button.dataset.riftCombatMode === "combat_session"
                    ? enterCombatFromPrompt(riftRoot, button)
                    : resolveCombatPlaceholder(riftRoot, button);
                transition.catch((error) => {
                    console.error(error);
                    button.disabled = false;
                    button.classList.remove("is-pending");
                    button.textContent = "В бой!";
                });
            });
        }

        function bindHeartResultButtons(root) {
            const scope = root instanceof Element ? root : document;
            scope.querySelectorAll("[data-rift-dismiss-heart-result]").forEach((button) => {
                if (button.dataset.riftHeartDismissBound === "1") {
                    return;
                }
                button.dataset.riftHeartDismissBound = "1";
                button.addEventListener("click", (event) => {
                    event.preventDefault();
                    const riftRoot = button.closest("[data-rift-instance-id]");
                    if (!riftRoot) {
                        return;
                    }
                    riftRoot.classList.add("is-heart-dismissed");
                    riftRoot.classList.remove("has-heart-event");
                });
            });
        }

        function renderAccumulatedMap(canvas) {
            const world = canvas.querySelector(".rift-map-world");
            const root = canvas.closest("[data-rift-instance-id]");
            if (!world || !root) {
                return;
            }

            const riftInstanceId = root.dataset.riftInstanceId;
            const mapScopeId = root.dataset.riftMapScopeId;
            const mapView = parseMapView(root);
            let state = null;
            if (riftInstanceId && mapScopeId && mapView) {
                state = store.merge({ riftInstanceId, mapScopeId, mapView });
            }
            if (!state && riftInstanceId && mapScopeId) {
                state = store.read(riftInstanceId, mapScopeId);
            }
            if (!state || !state.current_coord) {
                return;
            }

            const nodes = state.nodes || {};
            const nodeList = Object.values(nodes).filter(
                (node) => node && node.node_id && node.coord && shouldRenderNode(node, state.center_node_id)
            );
            const edges = Object.values(state.edges || {}).filter((edge) => edge && edge.from_node_id && shouldRenderEdge(edge));
            const positions = {};
            const fragment = document.createDocumentFragment();

            nodeList.forEach((node) => {
                positions[node.node_id] = nodePosition(node, state.current_coord);
            });

            edges.forEach((edge) => {
                const fromNode = nodes[edge.from_node_id];
                const toNode = edge.to_node_id ? nodes[edge.to_node_id] : null;
                if (!fromNode || !toNode || !positions[fromNode.node_id] || !positions[toNode.node_id]) {
                    return;
                }

                const direction = edgeDirection(positions[fromNode.node_id], positions[toNode.node_id]);
                if (!direction) {
                    return;
                }
                fragment.append(createEdge(edge, direction, positions[fromNode.node_id]));
            });

            nodeList.forEach((node) => {
                fragment.append(createNode(node, positions[node.node_id], state.center_node_id, state.heading));
            });

            world.replaceChildren(fragment);
            initialiseTooltips(world);
        }

        function bindCanvas(canvas) {
            if (!canvas || canvas.dataset.riftPanReady === "1") {
                return;
            }

            canvas.dataset.riftPanReady = "1";
            renderAccumulatedMap(canvas);
            let activePointerId = null;
            let startClientX = 0;
            let startClientY = 0;
            let startPanX = 0;
            let startPanY = 0;

            canvas.addEventListener("pointerdown", (event) => {
                if (event.button !== undefined && event.button !== 0) {
                    return;
                }

                activePointerId = event.pointerId;
                startClientX = event.clientX;
                startClientY = event.clientY;
                startPanX = numberFromStyle(canvas, "--rift-pan-x");
                startPanY = numberFromStyle(canvas, "--rift-pan-y");
                canvas.classList.add("is-dragging");
                canvas.setPointerCapture(event.pointerId);
            });

            canvas.addEventListener("pointermove", (event) => {
                if (event.pointerId !== activePointerId) {
                    return;
                }

                const nextX = startPanX + event.clientX - startClientX;
                const nextY = startPanY + event.clientY - startClientY;
                canvas.style.setProperty("--rift-pan-x", `${nextX}px`);
                canvas.style.setProperty("--rift-pan-y", `${nextY}px`);
            });

            function release(event) {
                if (event.pointerId !== activePointerId) {
                    return;
                }

                activePointerId = null;
                canvas.classList.remove("is-dragging");
            }

            canvas.addEventListener("pointerup", release);
            canvas.addEventListener("pointercancel", release);
            canvas.addEventListener("dblclick", () => {
                canvas.style.setProperty("--rift-pan-x", "0px");
                canvas.style.setProperty("--rift-pan-y", "0px");
            });
        }

        function bindResetButtons(root) {
            const scope = root instanceof Element ? root : document;
            scope.querySelectorAll("[data-rift-reset-map]").forEach((button) => {
                if (button.dataset.riftResetReady === "1") {
                    return;
                }

                button.dataset.riftResetReady = "1";
                button.addEventListener("click", () => {
                    const riftRoot = button.closest("[data-rift-instance-id]");
                    const riftInstanceId = riftRoot ? riftRoot.dataset.riftInstanceId : null;
                    if (riftInstanceId) {
                        store.reset(riftInstanceId);
                    }
                }, true);
            });
        }

        function init(root) {
            const scope = root instanceof Element ? root : document;
            bindResetButtons(scope);
            bindTravelButtons(scope);
            bindCombatPromptActions(scope);
            bindHeartResultButtons(scope);
            refreshCatalog(scope);
            refreshTooltips(scope);
            scope.querySelectorAll("[data-rift-map-canvas]").forEach((canvas) => {
                bindCanvas(canvas);
                renderAccumulatedMap(canvas);
            });
        }

        return {
            init,
        };
    }

    const store = window.RiftMapStore || createRiftMapStore();
    const pan = window.RiftMapPan || createRiftMapPan(store);

    window.RiftMapStore = store;
    window.RiftMapPan = pan;
    window.GameStates = window.GameStates || {};
    window.GameStates.rift = {
        init: pan.init,
    };
})();
