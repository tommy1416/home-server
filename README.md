# home-server

Personal home server documentation

## Nextcloud

Runs behind the nginx reverse proxy. Listens on `127.0.0.1:8080`.

### Access

| URL | Status | Notes |
|---|---|---|
| `https://tdemers.duckdns.org/nextcloud/` | ✅ Works (external only) | Primary access via domain — router doesn't support hairpin NAT |
| `https://tdemers.duckdns.org/` | ✅ Works (external only) | Redirects to /nextcloud/ via catch-all proxy |
| `http://192.168.0.31/nextcloud/` | ✅ Works | Local HTTP access — `proxy_redirect` rewrites Nextcloud's 302 to local host |
| `http://127.0.0.1/nextcloud/` | ✅ Works | Local HTTP access — same proxy_redirect fix |
| `https://192.168.0.31/` | ❌ Cert mismatch | SSL cert only covers `tdemers.duckdns.org` |

### Known issues

- **Hairpin NAT / NAT loopback:** The router doesn't route `tdemers.duckdns.org` requests from inside the LAN back to the server. Accessing Nextcloud via the domain only works from outside the home network. Local users must use `http://192.168.0.31/nextcloud/` instead.
- **SSL cert scope:** The Let's Encrypt cert only covers `tdemers.duckdns.org`. HTTPS via local IP (`192.168.0.31`, `127.0.0.1`) produces browser certificate warnings.
- **Mixed-content warnings:** Nextcloud's config references `tdemers.duckdns.org` for some assets, causing failed resource loads when accessed via local IPs. Functionality (login, file sync) is unaffected.

### Nginx fix applied

When Nextcloud is accessed via HTTP reverse proxy, it returns a 302 redirect to `https://tdemers.duckdns.org/nextcloud/login`. Since that domain is unreachable from the LAN, the fix was to add `proxy_redirect` rules:

- **`/etc/nginx/default.d/services.conf`** — proxy locations mirroring the SSL server block for the HTTP default server (port 80)
- The `/nextcloud/` location includes `proxy_redirect https://tdemers.duckdns.org/ http://$host/;` to rewrite redirects to the local host

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