# Backend Architecture Preview

## Goal

Backend is a FastAPI monolith with explicit feature boundaries. The project should not recreate the old `domains + SystemDispatcher + shared Redis managers` shape. Old code in `temp/` is a domain donor, not a direct source tree to copy.

The main rule is ownership: a feature owns its data, repositories, runtime services, events, and workers. Other features do not import its internal services or repositories directly.

## Dependency Rules

Allowed:

- `features/* -> core`
- `features/* -> resources`
- `features/* -> own package internals`
- `features/* -> stable event/task contracts`

Avoid:

- direct imports between gameplay feature services
- shared game repositories under a global `database/repositories`
- global Redis managers that know every domain
- a new central dispatcher that replaces feature ownership

`core` may expose infrastructure primitives: settings, logging, database session factory, Redis client factory, ARQ setup, base schemas, exceptions, and event/task interfaces. It should not own game domain behavior.

## Data Ownership

Database access is intentionally limited by data type.

DB-owner features:

- `auth`: users, credentials, refresh tokens, auth dependencies.
- `site`: public or pre-game website content, if needed.
- `chat`: chat rooms, messages, moderation, history.
- `world`: persistent/generated world data, world startup, world cache.
- `actor_state`: durable game actor/player state and DB-to-Redis lifecycle.

Runtime gameplay features:

- `combat`
- `inventory`
- `exploration`
- `scenario`
- `game_menu`
- `arena`

Runtime gameplay features normally work with Redis snapshots, Redis Streams/events, and ARQ tasks. They should not read or write the game database directly.

## Actor State

`actor_state` is the planned replacement for the useful parts of the old `context_assembler` plus the old account/context/inventory Redis managers.

Responsibilities:

- hydrate actor snapshots from DB into Redis
- persist Redis snapshots back to DB
- track dirty actors
- batch-save dirty actors through ARQ
- safety flush actors even when explicit save signals are missed
- define snapshot scopes such as `full`, `combat`, `inventory`, `exploration`, `status`

Expected flow:

1. Auth identifies the user.
2. The player selects or creates a character through the game entry flow.
3. `actor_state` hydrates the actor snapshot from DB into Redis.
4. Gameplay features mutate their own Redis snapshot slices.
5. Mutating features mark the actor dirty or emit an event.
6. ARQ workers persist dirty actors in batches.
7. Safety workers periodically flush stale dirty actors.

## World

`world` may own its own database tables because world data is not player state. It can load or generate world data on startup, prepare runtime views, and publish/cache data for gameplay features.

Gameplay features should consume prepared world runtime data through Redis/cache/service boundaries, not through `world` repositories.

## Auth

`auth` is a standalone feature. The PinLite backend may be used only as a donor for auth ideas and code: password hashing, token creation, refresh-token rotation, login/register/logout routes, and current-user dependencies.

PinLite's broader `apps/`, `media`, and global repository layout should not be copied as the project architecture.

## Target Skeleton

```text
src/backend/
  core/
  config/
  api/
  features/
    auth/
    site/
    chat/
    world/
    actor_state/
    combat/
    inventory/
    exploration/
    scenario/
    game_menu/
    arena/
```

Each feature may contain only the folders it actually needs:

```text
api/
dto/
models/
repositories/
services/
dependencies/
events/
workers/
runtime/
```

Folder responsibilities:

- `api/`: FastAPI routers and HTTP boundary code.
- `dto/`: backend DTOs owned by the feature, unless the model is a shared API contract.
- `models/`: SQLAlchemy ORM models owned by the feature.
- `repositories/`: persistence/cache access owned by the feature. It may contain subfolders such as `db/` and `redis/`.
- `services/`: feature use cases and application/domain logic.
- `dependencies/`: FastAPI dependency providers and local wiring.
- `events/`: event contracts, publishers, subscribers, and stream-facing adapters.
- `workers/`: background jobs and ARQ worker tasks.
- `runtime/`: internal engines, processors, or runtime services for gameplay features.

This is a standard folder vocabulary, not a requirement to create empty folders everywhere. Features should use the same folder names when a layer exists, but file names inside those folders should be specific to the feature's use cases.

## Account, Auth, Lobby, and Actor Boundaries

`auth` owns site/account authorization, not characters.

Responsibilities:

- user registration
- password login
- token issuing and refresh
- logout
- current user resolution
- future identity providers such as Google OAuth

`auth.User` is the account identity root. A user may exist without any game characters.

Use these terms consistently:

- `User` / `Account`: the site account and authorization identity
- `Character`: a persistent game character owned by a user
- `Actor`: the active runtime form of a selected character, usually hydrated into Redis

The user login flow must not create `actor_state`. Actor state appears only after the user enters the game with a selected character.

Expected high-level flow:

```text
anonymous browser
  -> auth login/register
  -> authenticated site user
  -> account/cabinet or game lobby
  -> select/create character in game lobby
  -> enter game
  -> actor_state hydrates selected character
```

Recommended feature split:

```text
src/backend/features/
  auth/          # users, credentials, tokens, current user
  account/       # account/cabinet profile and settings, no actor runtime
  site/          # public site content
  game_lobby/    # character list/create/delete/enter before active game
  actor_state/   # runtime actor snapshots and persistence lifecycle
```

`game_lobby` should use `auth.get_current_user`. It should not accept `user_id` from browser routes.

`Character.user_id` should reference `auth_users.id`. `auth.User` should not need a hard dependency on game character models.

The old `temp/backend/domains/user_features/account` code is a donor, not a target feature. It should be split during migration:

- old Telegram registration/user code: do not copy directly into `auth`
- `lobby_service.py`: donor for `game_lobby/services/lobby_service.py`
- `login_service.py`: donor for `game_lobby/services/enter_game_service.py`
- `account_session_service.py`: donor for `actor_state`, not site auth
- `onboarding_service.py`: donor for an onboarding feature or for a game-lobby onboarding entry flow

This is a starting structure, not a final framework. The first implementation pass should keep containers and event abstractions small, then harden the rules as real feature interactions appear.
