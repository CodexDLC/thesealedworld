# CI/CD и слой управления деплоем

## Цель

Разделить эксплуатацию проекта на независимые слои, чтобы после сборки образов можно было перезапускать сайт, игру и инфраструктуру отдельно.

Главная цель: сайт должен оставаться живым, даже если игровой backend, workers или chat/ws перезапускаются.

Operational contract для границ ответственности и перезапуска описан в [контракте деплоя](deployment-contract.md).

## Слои

Production compose нужно вести к трем слоям:

```text
infra
  postgres
  redis
  networks
  volumes
  reverse proxy, если он нужен

site
  frontend/site
  site migrations/job

game
  backend/game api
  chat/ws
  arq workers
  game/chat migrations/job
```

Локально можно временно оставить один удобный `deploy/docker-compose.yml`. Разделение локального запуска можно делать позже, когда production split станет стабильным.

## Чат

Chat/ws сервис не должен подниматься только в момент логина персонажа.

Правильная модель:

```text
chat/ws process запущен вместе с game runtime
browser websocket подключается только когда пользователь вошел в игру/персонажа
```

Если игра на maintenance, site показывает недоступность игровых поверхностей, но site auth, public pages, cabinet и library продолжают работать.

## CI

На push и pull request проверяется весь репозиторий:

```text
lint
frontend tests
backend tests
shared tests
docs build
image build
```

Причина: код лежит в одном repository, shared contracts общие, frontend и backend могут ломать друг друга через DTO, tokens, headers и API clients.

## Versioned Images

Сборка образов должна быть привязана к версии и commit SHA.

Рекомендуемые теги:

```text
registry/turnbasedmmorpg-site:<version>
registry/turnbasedmmorpg-site:<git-sha>

registry/turnbasedmmorpg-game:<version>
registry/turnbasedmmorpg-game:<git-sha>

registry/turnbasedmmorpg-chat:<version>
registry/turnbasedmmorpg-chat:<git-sha>

registry/turnbasedmmorpg-worker:<version>
registry/turnbasedmmorpg-worker:<git-sha>
```

`latest` можно публиковать как удобный alias, но production deploy не должен зависеть только от `latest`.

Источник версии:

```text
git tag vX.Y.Z
или version из pyproject.toml для dev/pre-release сборок
```

Для production предпочтительнее release tag. Commit SHA нужен для точного rollback.

## Документация

Сборка документации является частью CI перед публикацией образов.

Минимальная цель:

```powershell
uv run mkdocs build --clean
```

Если документация не собирается, release image не должен считаться готовым.

## CD

После merge в `main` pipeline должен:

```text
1. прогнать проверки всего кода;
2. собрать документацию;
3. собрать immutable images;
4. запушить images в registry;
5. остановиться на manual deploy gate.
```

Production deploy запускается вручную. Нужны отдельные команды/джобы:

```text
deploy infra
deploy site
deploy game
deploy full
```

`deploy site` не должен перезапускать game api, chat/ws и workers.

`deploy game` не должен перезапускать site, кроме случаев явного изменения reverse proxy или общего env контракта.

## Compose Files

Целевая production форма:

```text
deploy/compose.infra.yml
deploy/compose.site.yml
deploy/compose.game.yml
deploy/compose.tg-bot.yml
deploy/compose.prod.yml        # optional aggregator
deploy/compose.local.yml       # optional local override later
```

Примеры команд:

```powershell
docker compose -f deploy/compose.infra.yml up -d
docker compose -f deploy/compose.site.yml up -d --pull always
docker compose -f deploy/compose.game.yml up -d --pull always
docker compose -f deploy/compose.tg-bot.yml up -d --pull always
```

Перед принятием compose changes нужно проверять:

```powershell
docker compose -f deploy/compose.infra.yml config
docker compose -f deploy/compose.site.yml config
docker compose -f deploy/compose.game.yml config
docker compose -f deploy/compose.tg-bot.yml config
```

## Management Layer

Под management layer здесь понимается не runtime module, а эксплуатационный слой проекта:

```text
release version
image build
image registry
compose layer selection
manual deployment gate
rollback target
docs build
```

Этот слой должен быть описан в документации и CI/CD, но не должен протекать в gameplay code.

## Rollback

Rollback должен быть возможен по commit SHA:

```text
site -> предыдущий site image sha
game -> предыдущий game/chat/worker image sha
infra -> только ручной rollback после отдельного плана
```

Game rollback требует осторожности из-за Redis sessions, workers и миграций. Для game deploy лучше иметь manual maintenance mode на site.

## Текущее состояние

Production split уже вынесен в отдельные compose-файлы:

```text
deploy/compose.infra.yml
deploy/compose.site.yml
deploy/compose.game.yml
deploy/compose.tg-bot.yml
deploy/compose.prod.yml
```

CI уже собирает документацию и проверяет Docker build. Release images собираются отдельным workflow, а production deploy запускается вручную через layer-specific workflow.

Следующий практический шаг перед реальным production rollout: проверить на сервере layer-specific деплой и подтвердить, что `deploy site` не трогает game services, а `deploy game` не трогает site service.

## Generated Assets и S3

Сгенерированные изображения должны ссылаться на канонический `storage_key` и публичный URL под
`/static/generated-assets/<storage_key>`. Production может хранить bytes в S3-compatible Object Storage,
но код и база не должны зависеть от прямых bucket URLs.

Для Hetzner Object Storage в Nuremberg использовать примерный контракт:

```env
ASSET_STORAGE_BACKEND=s3
ASSET_PUBLIC_BASE_URL=/static/generated-assets
ASSET_S3_BUCKET=thesealedworld-generated-assets
ASSET_S3_REGION=nbg1
ASSET_S3_ENDPOINT_URL=https://nbg1.your-objectstorage.com
ASSET_S3_ACCESS_KEY_ID=<secret>
ASSET_S3_SECRET_ACCESS_KEY=<secret>
```

Когда `ASSET_STORAGE_BACKEND=s3`, frontend отдаёт `/static/generated-assets/<storage_key>`
из Object Storage. Не сохранять прямые provider bucket URLs в статьях, монстрах или future generated
content: публичный контракт сайта остаётся `/static/generated-assets/...`.

Перед переносом production assets сначала выполнить dry-run:

```powershell
uv run python scripts/backfill_generated_assets_to_s3.py --local-root var/generated-assets --dry-run
```

Реальный backfill должен копировать файлы, а не регенерировать изображения. Старый volume нужно оставить
как rollback/cache минимум на один release.
