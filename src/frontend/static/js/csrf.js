(function () {
    'use strict';

    var META_SELECTOR = 'meta[name="csrf-token"]';
    var HEADER_NAME = 'X-CSRF-Token';

    function getToken() {
        var meta = document.querySelector(META_SELECTOR);
        return meta ? meta.getAttribute('content') : '';
    }

    var UNSAFE_METHODS = { POST: true, PUT: true, PATCH: true, DELETE: true };

    // Patch global fetch so same-origin AJAX automatically carries the token.
    if (window.fetch) {
        var originalFetch = window.fetch.bind(window);
        window.fetch = function (input, init) {
            init = init || {};
            var method = (init.method || (typeof input === 'object' && input.method) || 'GET').toUpperCase();
            if (UNSAFE_METHODS[method]) {
                var headers = new Headers(init.headers || (typeof input === 'object' && input.headers) || undefined);
                if (!headers.has(HEADER_NAME)) {
                    var token = getToken();
                    if (token) headers.set(HEADER_NAME, token);
                }
                init.headers = headers;
            }
            return originalFetch(input, init);
        };
    }

    // HTMX integration: attach the token to every htmx request.
    document.addEventListener('htmx:configRequest', function (event) {
        var token = getToken();
        if (token) {
            event.detail.headers[HEADER_NAME] = token;
        }
    });
})();
