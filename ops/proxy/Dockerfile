# Reverse proxy: Caddy with this repository's Caddyfile built in, so that a
# change to the file reaches the server as a new image on the next deploy.
FROM caddy:2-alpine

COPY ops/proxy/Caddyfile /etc/caddy/Caddyfile
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
