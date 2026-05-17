# Deploy Management Layer

This directory contains the local development compose file plus the production split used by CI/CD.

## Local Nginx Smoke Layer

The default developer stack remains:

```powershell
docker compose -f deploy/docker-compose.yml up -d --build
```

To test the reverse proxy locally without changing that flow:

```powershell
docker compose -f deploy/docker-compose.yml -f deploy/compose.nginx-test.yml up -d --build
python tools/deploy/nginx_smoke.py
```

The smoke check targets `http://127.0.0.1:8080` and verifies nginx, frontend, backend, chat, static files, and backend OpenAPI routing through nginx.

## Production Layers

Production deploy is split by operational boundary:

```powershell
docker compose -f deploy/compose.infra.yml config
docker compose -f deploy/compose.site.yml config
docker compose -f deploy/compose.game.yml config
docker compose -f deploy/compose.prod.yml config
```

Required image variables:

```text
DOCKER_IMAGE_SITE
DOCKER_IMAGE_GAME
DOCKER_IMAGE_CHAT
DOCKER_IMAGE_WORKER
DOCKER_IMAGE_NGINX
```

Deploy rules:

- `infra` owns postgres, redis, nginx, certbot, networks, and volumes.
- `site` owns frontend/site and site migrations.
- `game` owns backend/game API, chat/ws, workers, and game/chat migrations.
- `site` deploys must not restart game services.
- `game` deploys must not restart the site service.
