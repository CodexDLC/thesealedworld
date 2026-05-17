#!/bin/sh
set -eu

PROJECT_NAME="${PROJECT_NAME:-tbmmorpg}"
COMPOSE_NETWORK="${COMPOSE_NETWORK:-tbmmorpg-network}"
CERTS_VOLUME="${CERTS_VOLUME:-tbmmorpg-certs}"
CHALLENGE_VOLUME="${CHALLENGE_VOLUME:-tbmmorpg-certbot-challenge}"
NGINX_CONTAINER="${NGINX_CONTAINER:-tbmmorpg-nginx}"
CERTBOT_IMAGE="${CERTBOT_IMAGE:-certbot/certbot:v2.11.0}"

docker run --rm \
  --name "${PROJECT_NAME}-certbot-renew" \
  --network "${COMPOSE_NETWORK}" \
  -v "${CERTS_VOLUME}:/etc/letsencrypt" \
  -v "${CHALLENGE_VOLUME}:/var/www/certbot" \
  "${CERTBOT_IMAGE}" renew --quiet

docker exec "${NGINX_CONTAINER}" nginx -s reload
