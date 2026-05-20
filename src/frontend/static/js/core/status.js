/**
 * Character status refresh is event-driven through HTMX.
 *
 * Inventory and future realtime channels should emit `character-status-refresh`;
 * the status panel owns the fetch target in its template.
 */
window.CharacterStatus = {
    refresh() {
        if (window.htmx) {
            window.htmx.trigger(document.body, 'character-status-refresh');
        }
    },
};
