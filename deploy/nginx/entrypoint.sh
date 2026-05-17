#!/bin/sh
set -eu

DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
LIVE_CERT_DIR="/etc/letsencrypt/live/${DOMAIN_NAME}"
LIVE_CERT="${LIVE_CERT_DIR}/fullchain.pem"
LIVE_KEY="${LIVE_CERT_DIR}/privkey.pem"

if [ -f "$LIVE_CERT" ] && [ -f "$LIVE_KEY" ]; then
    TLS_CERTIFICATE_PATH="$LIVE_CERT"
    TLS_CERTIFICATE_KEY_PATH="$LIVE_KEY"
else
    FALLBACK_CERT_DIR="/tmp/letsencrypt/live/${DOMAIN_NAME}"
    TLS_CERTIFICATE_PATH="${FALLBACK_CERT_DIR}/fullchain.pem"
    TLS_CERTIFICATE_KEY_PATH="${FALLBACK_CERT_DIR}/privkey.pem"
    mkdir -p "$FALLBACK_CERT_DIR"
    openssl req \
        -x509 \
        -nodes \
        -newkey rsa:2048 \
        -days 7 \
        -subj "/CN=${DOMAIN_NAME}" \
        -keyout "$TLS_CERTIFICATE_KEY_PATH" \
        -out "$TLS_CERTIFICATE_PATH" >/dev/null 2>&1
fi

export DOMAIN_NAME TLS_CERTIFICATE_PATH TLS_CERTIFICATE_KEY_PATH

envsubst '${DOMAIN_NAME} ${TLS_CERTIFICATE_PATH} ${TLS_CERTIFICATE_KEY_PATH}' \
    < /etc/templates/site.conf.template \
    > /etc/nginx/conf.d/site.conf

exec nginx -g 'daemon off;'
