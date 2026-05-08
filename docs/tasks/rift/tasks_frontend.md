# Rift Frontend Tasks

These tasks describe the browser-facing rift experience.

## Expected Feature Ownership

Expected frontend folders:

```text
src/frontend/game_features/rift/
src/frontend/templates/game/domains/rift/
src/frontend/integrations/backend_api/rift.py
```

Rift UI should render through the game session shell. Templates should not import backend internals.

## Contract Board UI

The board should feel like an adventurers guild notice board:

- 5-6 paper notices.
- Each notice should show tier, task type, setting/risk/reward, and rough distance.
- Details can expand on click.
- Notices may include weaker, equal, and harder options.

Needs owner decision:

- Exact notice fields visible before click.
- Whether the board is in a guild page, city/hub screen, game menu, or exploration location.

## Travel UI

Travel should preserve expedition pacing:

- Player accepts contract.
- Route to entrance appears.
- Encounter/event feed can update along the way.
- Portal shortcuts can appear later.

Needs owner decision:

- Is travel shown as a route screen, event log, map path, or background timer with interrupts?

## Rift Run UI

Rift screen should be browser-first, not Telegram-style buttons only.

Candidate surfaces:

- Center: current node scene or stylized graph.
- Left: character/symbiote/rift danger status.
- Right: route choices and scan information.
- Bottom: event log, symbiote commentary, rewards gained.
- Overlay/card: combat result, core action, rare event.

Needs owner decision:

- Literal map, stylized graph, or scene-first view with route cards.
- How much symbiote commentary appears.
- How visible undiscovered graph nodes should be.

## Dirty Reward UI

Rift UI should make dirty loot clear:

- Unsynced reward buffer.
- Secured versus dirty status.
- Warning on death/exit risk.
- Sync moment at city/portal.

Needs owner decision:

- Visual language for dirty loot.
- Whether first MVP needs full inventory integration UI or a simpler run reward panel.

## Frontend Tests

Add tests for:

- Contract board template contract.
- Rift run template contract.
- Backend API client method paths.
- Session context routing to `rift` domain.
- Dirty reward display states.
