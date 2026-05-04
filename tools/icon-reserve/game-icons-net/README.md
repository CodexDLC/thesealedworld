# Game-icons.net Reserve

This folder keeps the full downloaded Game-icons.net SVG pack outside the frontend runtime static tree.

## Files

- `transparent/` contains the raw SVG pack grouped by author folder.
- `browser.html` is a local file browser for reviewing icons visually.
- `build-browser.ps1` regenerates `browser.html` from the current SVG files.

## Workflow

Open `browser.html` directly in a browser or IDE preview and search by filename, author, or path.

When an icon is selected for the game UI, copy it into a runtime folder such as:

```text
src/frontend/static/images/ui/scenario-choice-icons/
src/frontend/static/images/ui/skill-icons/
src/frontend/static/images/ui/card-icons/
```

Keep scenario and gameplay data semantic, for example `icon: "warning"`, and map that key to the selected runtime SVG in frontend code.

Record attribution for every copied or adapted icon before public release.
