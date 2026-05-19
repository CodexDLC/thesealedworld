# Контракт деплоя

## Цель

Production deploy разделен на независимые operational layers, чтобы сайт оставался доступным во время перезапуска или обслуживания игрового runtime.

Этот контракт фиксирует не только расположение файлов, но и допустимое поведение deploy-команд.

## Ownership Matrix

| Слой | Владеет | Миграции | Допустимый restart scope | Rollback target |
| --- | --- | --- | --- | --- |
| `infra` | Postgres, Redis, Nginx, certbot helper, networks, volumes | Нет прикладных миграций | Только infra-сервисы | Ручной rollback после отдельного плана |
| `site` | `frontend` / site-web, site static/generated assets mount | `site` schema через frontend Alembic | `site-migrate`, `frontend` | Предыдущий `site` image SHA |
| `game` | Backend/game API, chat/ws, ARQ workers, game runtime mounts | `game` и `chat` schemas через backend migration command | `backend-migrate`, `backend`, `chat`, workers | Предыдущие `game`, `chat`, `worker` image SHA |

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
deploy/compose.prod.yml
```

`compose.prod.yml` является агрегатором для проверки или осознанного full-stack сценария. Он не должен становиться обычной командой для site-only или game-only деплоя.

## Image Contract

Production deploy принимает один `image_ref` и выставляет layer images:

```text
DOCKER_IMAGE_SITE=ghcr.io/<repo>-site:<image_ref>
DOCKER_IMAGE_GAME=ghcr.io/<repo>-game:<image_ref>
DOCKER_IMAGE_CHAT=ghcr.io/<repo>-chat:<image_ref>
DOCKER_IMAGE_WORKER=ghcr.io/<repo>-worker:<image_ref>
DOCKER_IMAGE_NGINX=ghcr.io/<repo>-nginx:<image_ref>
```

Для production rollback использовать commit SHA или release tag. `latest` может существовать как удобный alias, но не должен быть единственным production target.

## Env и Secrets

Deploy workflow получает production `.env` из GitHub secret `ENV_FILE` и записывает его на сервер перед запуском Compose.

Правила:

- secrets не хранить в репозитории;
- значения `.env` с символом `$` экранировать как `$$`, иначе Docker Compose применит interpolation;
- site/game deploy может читать общий `.env`, но не должен перезапускать чужой слой из-за изменения переменной без явного full/infra плана.

## Runtime Boundary

- Код из `src/` не должен зависеть от `deploy/`.
- `deploy/` не должен импортировать gameplay/runtime internals напрямую.
- Взаимодействие deploy layer с runtime происходит через published operational contracts: image tags, env vars, entrypoints, health endpoints и migration commands.

## Проверки перед деплоем

```powershell
docker compose -f deploy/compose.infra.yml config
docker compose -f deploy/compose.site.yml config
docker compose -f deploy/compose.game.yml config
docker compose -f deploy/compose.prod.yml config
```

Для certbot profile:

```powershell
docker compose -f deploy/compose.infra.yml config --services
docker compose -f deploy/compose.infra.yml --profile manual config --services
```

`certbot` должен отсутствовать в обычном списке сервисов и появляться только с `--profile manual`.
