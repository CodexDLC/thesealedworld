# Integrations

Frontend/site взаимодействует с game backend через typed HTTP clients under:

```text
src/frontend/integrations/backend_api/
```

Frontend code не импортирует backend feature internals напрямую.

## Site-To-Game Calls

Site-owned routes и game-facing frontend features используют backend API clients
для game-backed данных и действий.

Правила:

- outbound requests к backend/game добавляют configured internal service key;
- game lobby bootstrap/select/create/release/delete проходят через backend API;
- game-token cookies используются для game action routes;
- site auth не проксируется в backend как site-auth API;
- game-backed UI должен уметь показать unavailable/maintenance state, если
  backend недоступен.

## Game Tokens

Frontend хранит game token state отдельно от site auth token state:

```text
tbmmorpg_game_access_token
tbmmorpg_game_refresh_token
```

Game-token flow используется после выбора или создания персонажа. Backend
проверяет `character_id` scope на игровых action routes.

## Library And Public Game Data

Library/cabinet/ranking pages may read game data through backend APIs or future
site-owned projections. До отдельного решения такие страницы должны оставаться
за integration boundary и не импортировать backend internals.
