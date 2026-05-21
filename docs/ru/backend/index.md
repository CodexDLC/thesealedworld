# Backend

`src/backend/` — игровой backend сервиса. Он владеет gameplay API,
runtime-состоянием, воркерами, Redis Streams, игровыми схемами БД и chat/ws
после переноса chat в backend ownership.

Backend не рендерит публичный сайт и не владеет site-auth страницами,
кабинетом, библиотекой или site Alembic.

## Ownership

Backend владеет:

- game lobby API и game-token issuance;
- character lifecycle и проверками владения персонажем;
- active character sessions;
- game session;
- scenario;
- combat;
- exploration;
- inventory;
- arena;
- world и game catalog runtime;
- game workers;
- Redis Streams и runtime state;
- chat REST/ws, сервисами, моделями и воркерами;
- Alembic миграциями для `game` и `chat` schemas.

Backend не владеет:

- public site rendering;
- auth/account страницами сайта;
- cabinet rendering;
- library pages как site surface;
- `site` schema migrations.

## Database Schemas

Backend Alembic владеет только схемами:

```text
game
chat
```

Site-owned auth/user tables принадлежат frontend/site service. Игровые таблицы
хранят account ownership как UUID, без обязательного cross-schema FK на
`site.auth_users`.

Любой game API, который принимает `character_id` или `char_id`, обязан проверять:

```text
current_user.id == character.user_id
```

Клиентский ввод не является доказательством владения персонажем.

## Site-To-Game Boundary

Frontend/site обращается к backend/game только через HTTP-контракты и typed
clients. Frontend не импортирует backend internals.

Текущий site-to-game контракт:

- site requests отправляют `X-Internal-Service-Key`;
- `/game-lobby/bootstrap` получает site user context и возвращает персонажей
  пользователя;
- `/game-lobby/select` проверяет ownership, активирует персонажа и выдает
  `game_access` / `game_refresh`;
- `/game-lobby/create`, `/game-lobby/release-selected`,
  `/game-lobby/delete-character` используют тот же internal service boundary;
- `/game-lobby/refresh-token` обновляет game token pair.

Game token содержит:

```text
token_type = game_access | game_refresh
sub = user_uuid
character_id = game character id
session_id = game session id
exp
iat
```

Backend route dependencies извлекают `AuthenticatedUser` из `game_access` и
проверяют character scope на игровых action routes.

## Runtime Availability

Backend может перезапускаться независимо от site service. Когда backend
недоступен, frontend/site показывает game unavailable или maintenance state на
game-backed поверхностях.

Backend health endpoint остается простым operational contract:

```text
GET /health
```
