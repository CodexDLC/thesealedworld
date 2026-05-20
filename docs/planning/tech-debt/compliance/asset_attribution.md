# Asset Attribution TODO

## Game-icons.net

We plan to review the full Game-icons.net pack and reuse selected SVG icons for scenario choices, skill hints, warnings, item actions, and similar game UI glyphs.

Raw reserve location:

- `tools/icon-reserve/game-icons-net/transparent/`
- `tools/icon-reserve/game-icons-net/browser.html`
- `tools/icon-reserve/game-icons-net/build-browser.ps1`

Open `browser.html` directly as a local file to browse the pack by author folder. Use the search field to find icons by filename, author, or path. If the raw pack changes, rerun `build-browser.ps1` from the repository root.

First curated runtime pack:

- `src/frontend/static/images/ui/scenario-choice-icons/`
- Attribution file: `src/frontend/static/images/ui/scenario-choice-icons/ATTRIBUTION.md`

Useful review links:

- Tool icons: https://game-icons.net/tags/tool.html

Usage rules:

- Keep the full downloaded pack in `tools/icon-reserve/game-icons-net/`.
- Copy only selected runtime assets under `src/frontend/static/images/ui/`.
- Prefer semantic scenario icon keys such as `warning`, `strength`, `intellect`, `inspect`, and `loot`.
- Do not render raw icon keys as visible text in the UI.
- For every copied or adapted Game-icons.net icon, record:
  - local filename
  - original icon name
  - original author
  - source URL
  - license
- Create an attribution file near the asset pack, for example `src/frontend/static/images/ui/scenario-choice-icons/ATTRIBUTION.md`.
- Before public release, add a public `Credits` / `Lizenzen` page and link it from the footer.
- Keep this separate from `Datenschutz`, because privacy policy text is about personal data, not asset licensing.

Reference license note:

- Game-icons.net assets are published under CC BY 3.0, with some assets possibly Public Domain.
- CC BY 3.0 allows use and modification, including in public/commercial projects, with proper attribution.
