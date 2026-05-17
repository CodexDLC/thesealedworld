FROM nginx:1.27-alpine

RUN apk add --no-cache openssl && \
    rm /etc/nginx/conf.d/default.conf

ENV DOMAIN_NAME=localhost

COPY deploy/nginx/nginx.conf          /etc/nginx/nginx.conf
COPY deploy/nginx/site.conf.template  /etc/templates/site.conf.template
COPY deploy/nginx/entrypoint.sh       /entrypoint.sh

RUN mkdir -p /var/www/certbot && \
    chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
