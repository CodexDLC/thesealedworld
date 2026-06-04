"""Per-request source selection.

The Source Switcher dropdown in `base_studio.html` writes a cookie
`studio_source=<local|prod>`. `SourceSelectorMiddleware` reads the cookie,
falls back to `settings.studio_source` (env), and attaches the resolved
`Source` to `request.state.source` so downstream code (repositories,
backend_api clients) can fetch the active connection.
"""
