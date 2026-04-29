FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY deploy/nginx/nginx.conf      /etc/nginx/nginx.conf
COPY deploy/nginx/site-local.conf /etc/nginx/conf.d/site.conf

CMD ["nginx", "-g", "daemon off;"]
