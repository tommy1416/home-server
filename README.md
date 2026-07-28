# home-server

Personal home server documentation. Runs on Fedora 44 (Intel i7-9700K, AMD 290x, 1TB SSD, 4TB HDD).

## Nginx

Serves as the reverse proxy for all services behind a single domain.

### Main configuration

| File | Purpose |
|---|---|
| `/etc/nginx/nginx.conf` | Global settings — user, worker processes, logging, MIME types |
| `/etc/nginx/conf.d/nextcloud.conf` | All site routing — reverse proxy rules for every service |
| `/etc/nginx/conf.d/ollama-auth.conf` | Authentication/rate-limiting for the Ollama API |
| `/etc/nginx/default.d/*.conf` | Additional default server includes |

Backup is at [`nginx/nginx.conf`](nginx/nginx.conf).

### Server names

- `tdemers.duckdns.org` — primary domain, HTTPS (port 443) with Certbot SSL
- `192.168.0.31` — local IP, HTTPS (port 443) using the same cert
- `127.0.0.1` — loopback, handled by the default server on port 80

HTTP on port 80 either redirects `tdemers.duckdns.org` to HTTPS or serves the landing page for non-matching hosts.

### Routing table

| Path | Backend | Port | Notes |
|---|---|---|---|
| `/` | Nextcloud (default) | `127.0.0.1:8080` | Catch-all, also serves landing page from `/usr/share/nginx/html/` |
| `/nextcloud/` | Nextcloud | `127.0.0.1:8080` | Explicit path with `X-Forwarded-Prefix` |
| `/v1/` | Ollama API proxy | `127.0.0.1:4000` | Auth-protected, rate-limited (8 burst, 4 concurrent) |
| `/copilot/` | Local Copilot UI | static `/srv/local-copilot/` | GitHub Copilot dashboard |
| `/api/models` | Ollama models list | `127.0.0.1:11434/api/tags` | Public (no auth) |
| `/api/chat` | Ollama chat completions | `127.0.0.1:11434/v1/chat/completions` | Public (no auth), max body 128k |
| `/pihole/` | Pi-hole | `10.88.0.3:80` | LAN only (192.168.0.0/24) |
| `/netdata/` | Netdata | `127.0.0.1:19999` | LAN only (192.168.0.0/24), WebSocket support |
| `/vaultwarden/` | Vaultwarden | `127.0.0.1:8222` | WebSocket support, max body 128M |

### SSL

Managed by **Certbot** for `tdemers.duckdns.org`:
- Certificate: `/etc/letsencrypt/live/tdemers.duckdns.org/fullchain.pem`
- Key: `/etc/letsencrypt/live/tdemers.duckdns.org/privkey.pem`
- Options: `/etc/letsencrypt/options-ssl-nginx.conf`
- DH params: `/etc/letsencrypt/ssl-dhparams.pem`

### Notable settings

- `client_max_body_size 10G` — allows large uploads (Nextcloud)
- `proxy_read_timeout 3600` — long timeout for Nextcloud sync
- `proxy_request_buffering off` — streaming support for various backends
- Connection upgrade map for WebSocket proxying

### Landing page

Served from `/usr/share/nginx/html/index.html` as a static service index with links to all services. This is what you see at `http://127.0.0.1/` or `http://192.168.0.31/`.