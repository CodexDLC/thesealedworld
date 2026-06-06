# Deploy Management Layer

This directory contains the local development compose file plus the production split used by CI/CD.

## Local Nginx Smoke Layer

The default developer stack remains:

```powershell
docker compose -f deploy/docker-compose.yml up -d --build
```

The local stack runs two frontend surfaces from the same frontend codebase:

- `frontend` / `tbmmorpg-frontend-site` on `http://127.0.0.1:8000` with `FRONTEND_SURFACE=site`.
- `frontend-play` / `tbmmorpg-frontend-play` on `http://127.0.0.1:8003` with `FRONTEND_SURFACE=play`.

The site surface routes `/play` to the play surface when `frontend-play` is healthy.
If the play container is stopped, the site stays online and renders the in-site
technical maintenance state instead of sending users to a broken lobby:

```powershell
docker compose -f deploy/docker-compose.yml stop frontend-play
```

To test the reverse proxy locally without changing that flow:

```powershell
docker compose -f deploy/docker-compose.yml -f deploy/compose.nginx-test.yml up -d --build
python tools/deploy/nginx_smoke.py
```

The local nginx smoke layer uses one nginx container, matching production host-based routing:

- `http://thesealed.localhost:8080` -> site frontend.
- `http://play.thesealed.localhost:8080` -> play frontend.

In this nginx smoke mode the direct application host ports are reset, so
`frontend`, `frontend-play`, `backend`, and `chat` are reachable from the host
only through nginx.

Use the `thesealed.localhost` hosts for browser auth testing. They share the
local `.thesealed.localhost` auth cookie domain, unlike `localhost` and
`play.localhost`.

The smoke check targets `http://127.0.0.1:8080` and verifies nginx, frontend, backend, chat, static files, and backend OpenAPI routing through nginx.

Local email capture is available through Mailpit:

- SMTP endpoint inside Docker: `mailpit:1025`
- Web UI on the host: `http://127.0.0.1:8025`

The local `frontend` container is wired to Mailpit automatically, so tester-flow emails can be inspected without a real SMTP account.

## Production Layers

Production deploy is split by operational boundary:

```powershell
docker compose -f deploy/compose.infra.yml config
docker compose -f deploy/compose.site.yml config
docker compose -f deploy/compose.game.yml config
docker compose -f deploy/compose.tg-bot.yml config
```

Required image variables:

```text
DOCKER_IMAGE_SITE
DOCKER_IMAGE_GAME
DOCKER_IMAGE_CHAT
DOCKER_IMAGE_WORKER
DOCKER_IMAGE_TG_BOT
DOCKER_IMAGE_NGINX
```

Deploy rules:

- `infra` owns postgres, redis, nginx, certbot helper profile, networks, and volumes.
- `site` owns frontend/site, frontend-play/play surface, and site migrations.
- `game` owns backend/game API, chat/ws, workers, and game/chat migrations.
- `tg-bot` owns the Telegram polling worker and Redis Stream news announcements.
- `site` deploys must not restart game services.
- `game` deploys must not restart the site service.
- `tg-bot` deploys must not restart site or game services.

Production nginx routes `DOMAIN_NAME` to `frontend` and `PLAY_DOMAIN_NAME` to
`frontend-play`. Both hosts keep `/api/`, `/chat/`, `/ws/chat`, and
`/ws/realtime` proxied to the game/chat layer.

## Production Admin Tools

The optional tools layer starts browser UIs for inspecting production data:

- CloudBeaver on server-local `127.0.0.1:8978` for PostgreSQL.
- RedisInsight on server-local `127.0.0.1:5540` for Redis.

These ports intentionally bind only to the server loopback interface. Do not
publish them through Nginx for the alpha environment.

Start or update the tools on the server:

```bash
cd /opt/turnbasedmmorpg/deploy
docker compose -f compose.tools.yml up -d
docker compose -f compose.tools.yml ps
```

Open an SSH tunnel from the operator workstation:

```powershell
ssh -N -L 8978:127.0.0.1:8978 -L 5540:127.0.0.1:5540 my_game
```

Then open locally:

- CloudBeaver: `http://127.0.0.1:8978`
- RedisInsight: `http://127.0.0.1:5540`

CloudBeaver connection settings:

```text
Host: postgres
Port: 5432
Database: tbmmorpg_site
User: value of POSTGRES_USER
Password: value of POSTGRES_PASSWORD
```

Create a second PostgreSQL connection for `tbmmorpg_game` with the same host,
port, user, and password.

RedisInsight connection settings:

```text
Host: redis
Port: 6379
Username: default or empty
Password: value of REDIS_PASSWORD
TLS: disabled
```

## Production TLS

Production TLS uses Let's Encrypt through the Nginx webroot flow. Do not use
`certbot standalone`; port `80` is owned by Nginx.

Nginx serves ACME challenges before HTTP-to-HTTPS redirect:

```nginx
location /.well-known/acme-challenge/ {
    root /var/www/certbot;
}
```

The infra layer owns two named volumes:

```text
tbmmorpg-certs              -> /etc/letsencrypt
tbmmorpg-certbot-challenge  -> /var/www/certbot
```

Nginx mounts both read-only. Certbot mounts both read-write only when it is run
manually or by the host renewal timer. The `certbot` service is intentionally
behind the `manual` profile, so normal deploy does not start a daemon container.

Verify that behavior locally:

```powershell
$env:DOMAIN_NAME="example.com"
$env:DOCKER_IMAGE_NGINX="tbmmorpg-nginx:test"
$env:POSTGRES_PASSWORD="example"  # pragma: allowlist secret
$env:REDIS_PASSWORD="example"  # pragma: allowlist secret
docker compose -f deploy/compose.infra.yml config --services
docker compose -f deploy/compose.infra.yml --profile manual config --services
```

`certbot` must be absent from the first service list and present in the second.

Before issuing a certificate, start the infra layer and verify the webroot:

```bash
export DOMAIN_NAME=example.com
docker compose -f deploy/compose.infra.yml up -d nginx

docker run --rm \
  -v tbmmorpg-certbot-challenge:/var/www/certbot \
  alpine sh -c 'mkdir -p /var/www/certbot/.well-known/acme-challenge && echo ok > /var/www/certbot/.well-known/acme-challenge/ping'

curl -i "http://${DOMAIN_NAME}/.well-known/acme-challenge/ping"
curl -i "http://www.${DOMAIN_NAME}/.well-known/acme-challenge/ping"
```

Both requests must return `200 OK` with `ok`.

Initial certificate issue:

```bash
docker run --rm \
  --name tbmmorpg-certbot-issue \
  --network tbmmorpg-network \
  -v tbmmorpg-certs:/etc/letsencrypt \
  -v tbmmorpg-certbot-challenge:/var/www/certbot \
  certbot/certbot:v2.11.0 certonly \
  --webroot \
  -w /var/www/certbot \
  -d "${DOMAIN_NAME}" \
  -d "www.${DOMAIN_NAME}" \
  --cert-name "${DOMAIN_NAME}"

docker exec tbmmorpg-nginx nginx -s reload
```

Install host renewal on the server:

```bash
install -m 0755 deploy/certbot/tbmmorpg-certbot-renew.sh /usr/local/sbin/tbmmorpg-certbot-renew.sh
install -m 0644 deploy/certbot/tbmmorpg-certbot-renew.service /etc/systemd/system/tbmmorpg-certbot-renew.service
install -m 0644 deploy/certbot/tbmmorpg-certbot-renew.timer /etc/systemd/system/tbmmorpg-certbot-renew.timer
systemctl daemon-reload
systemctl enable --now tbmmorpg-certbot-renew.timer
systemctl list-timers tbmmorpg-certbot-renew.timer
```

Equivalent cron schedule:

```cron
17 3,15 * * * root /usr/local/sbin/tbmmorpg-certbot-renew.sh
```

Certificate check:

```bash
echo | openssl s_client -servername "${DOMAIN_NAME}" -connect "${DOMAIN_NAME}:443" 2>/dev/null | openssl x509 -noout -dates -subject
```

If `.env` values contain `$`, escape each dollar as `$$`; otherwise Docker
Compose treats it as variable interpolation.
