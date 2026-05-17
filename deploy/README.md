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

- `infra` owns postgres, redis, nginx, certbot helper profile, networks, and volumes.
- `site` owns frontend/site and site migrations.
- `game` owns backend/game API, chat/ws, workers, and game/chat migrations.
- `site` deploys must not restart game services.
- `game` deploys must not restart the site service.

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
$env:POSTGRES_PASSWORD="example"
$env:REDIS_PASSWORD="example"
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
