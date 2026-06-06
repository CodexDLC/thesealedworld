# Контракт деплоя

## Цель

Production deploy разделен на независимые operational layers, чтобы сайт оставался доступным во время перезапуска или обслуживания игрового runtime.

Этот контракт фиксирует не только расположение файлов, но и допустимое поведение deploy-команд.

## Ownership Matrix

| Слой | Владеет | Миграции | Допустимый restart scope | Rollback target |
| --- | --- | --- | --- | --- |
| `infra` | Postgres, Redis, Nginx, certbot helper, networks, volumes | Нет прикладных миграций | Только infra-сервисы | Ручной rollback после отдельного плана |
| `site` | `frontend` / site-web, `frontend-play` / play surface, site static/generated assets mount | `site` schema через frontend Alembic | `site-migrate`, `frontend`, `frontend-play` | Предыдущий `site` image SHA |
| `game` | Backend/game API, chat/ws, ARQ workers, game runtime mounts | `game` и `chat` schemas через backend migration command | `backend-migrate`, `backend`, `chat`, workers | Предыдущие `game`, `chat`, `worker` image SHA |
| `tg-bot` | Telegram polling worker, Redis Stream news announcements | Нет прикладных миграций | `tg-bot` | Предыдущий `tg-bot` image SHA |

## Границы перезапуска

- `deploy site` не должен перезапускать `backend`, `chat` или workers.
- `deploy game` не должен перезапускать `frontend`.
- `deploy infra` не должен выполняться как побочный эффект site/game deploy.
- `deploy full` допустим только как осознанный full-stack rollout.
- Layer-specific deploy не должен использовать `--remove-orphans`, потому что соседние слои используют тот же Compose project name и могут быть ошибочно удалены как orphan-сервисы.

## Compose Files

Production deploy использует:

```text
deploy/compose.infra.yml
deploy/compose.site.yml
deploy/compose.game.yml
deploy/compose.tg-bot.yml
deploy/compose.prod.yml
```

`compose.prod.yml` является агрегатором для проверки или осознанного full-stack сценария и включает `infra`, `site`, `game` и `tg-bot`. Он не должен становиться обычной командой для site-only, game-only или tg-bot-only деплоя.

## Image Contract

Production deploy принимает один `image_ref` и выставляет layer images:

```text
DOCKER_IMAGE_SITE=ghcr.io/<repo>-site:<image_ref>
DOCKER_IMAGE_GAME=ghcr.io/<repo>-game:<image_ref>
DOCKER_IMAGE_CHAT=ghcr.io/<repo>-chat:<image_ref>
DOCKER_IMAGE_WORKER=ghcr.io/<repo>-worker:<image_ref>
DOCKER_IMAGE_TG_BOT=ghcr.io/<repo>-tg-bot:<image_ref>
DOCKER_IMAGE_NGINX=ghcr.io/<repo>-nginx:<image_ref>
```

Для production rollback использовать commit SHA или release tag. `latest` может существовать как удобный alias, но не должен быть единственным production target.

## Env и Secrets

Deploy workflow получает production `.env` из GitHub secret `ENV_FILE` и записывает его на сервер перед запуском Compose.

Правила:

- secrets не хранить в репозитории;
- значения `.env` с символом `$` экранировать как `$$`, иначе Docker Compose применит interpolation;
- site/game deploy может читать общий `.env`, но не должен перезапускать чужой слой из-за изменения переменной без явного full/infra плана.
- `BOOTSTRAP_CONTENT_MATERIALIZATION_ENABLED=True` разрешает backend startup синхронизировать статический/world/rift generated content без внешних AI-вызовов;
- `BOOTSTRAP_AI_GENERATION_ENABLED=False` является production default: backend startup не должен ставить AI generation tasks автоматически, даже если materialization создала локальные generated rows.

## Runtime Boundary

- Код из `src/` не должен зависеть от `deploy/`.
- `deploy/` не должен импортировать gameplay/runtime internals напрямую.
- Взаимодействие deploy layer с runtime происходит через published operational contracts: image tags, env vars, entrypoints, health endpoints и migration commands.

## Service Boundary

Production runtime разделен на site и game layers:

- `frontend` / site-web владеет public site, auth/account, cabinet, library,
  site templates/static и `site` schema migrations.
- `frontend-play` запускает тот же site image с `FRONTEND_SURFACE=play` и
  обслуживает gameplay entry/lobby под отдельным public host.
- `backend` / game владеет gameplay APIs, runtime state, workers, game catalog,
  chat/ws и `game` + `chat` schema migrations.
- Site обращается к game backend через typed HTTP clients и internal service key.
- Backend не рендерит public site.
- Site должен оставаться доступным при restart/maintenance game runtime.
- Nginx обязан маршрутизировать основной public domain на `frontend`, а play
  domain на `frontend-play`; оба host-а проксируют `/api/`, `/chat/`,
  `/ws/chat` и `/ws/realtime` в game/chat слой.
- Generated asset URLs остаются site-facing контрактом `/static/generated-assets/<storage_key>`.
  S3/Object Storage является backend storage implementation detail; прямые provider URLs не являются
  каноническими значениями для статей, монстров или будущих generated assets.

## Проверки перед деплоем

```powershell
docker compose -f deploy/compose.infra.yml config
docker compose -f deploy/compose.site.yml config
docker compose -f deploy/compose.game.yml config
docker compose -f deploy/compose.tg-bot.yml config
docker compose -f deploy/compose.prod.yml config
```

Для certbot profile:

```powershell
docker compose -f deploy/compose.infra.yml config --services
docker compose -f deploy/compose.infra.yml --profile manual config --services
```

`certbot` должен отсутствовать в обычном списке сервисов и появляться только с `--profile manual`.
