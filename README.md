# home-server

Personal home server documentation

## Nextcloud

Runs behind the nginx reverse proxy. Listens on `127.0.0.1:8080`.

Config backup: [`nextcloud/config.php`](nextcloud/config.php)

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

Backups:
- [`nginx/nginx.conf`](nginx/nginx.conf) — main config
- [`nginx/nextcloud.conf`](nginx/nextcloud.conf) — site routing / reverse proxy rules
- [`nginx/services.conf`](nginx/services.conf) — default server proxy locations for local HTTP access

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

## Clipboard

Minimal clipboard server — paste text from one device and retrieve it from another. No authentication, no database, just a big textarea behind a Python script.

| File | Purpose |
|---|---|
| `/usr/local/bin/clipboard-server.py` | Python HTTP server (~55 lines, stdlib only) |
| `/etc/systemd/system/clipboard.service` | systemd unit (runs as `tdemers`, auto-restarts) |
| `/var/lib/clipboard/clipboard.txt` | Clipboard data persisted to disk |

Backups:
- [`clipboard/clipboard-server.py`](clipboard/clipboard-server.py)
- [`clipboard/clipboard.service`](clipboard/clipboard.service)

### Access

| Route | URL | Notes |
|---|---|---|
| **LAN (HTTP)** | `http://192.168.0.31/clipboard/` | Path-based proxy via default server |
| **LAN (HTTPS)** | `https://192.168.0.31/clipboard/` | SSL via main server block (cert warning for the IP) |
| **Localhost** | `http://127.0.0.1/clipboard/` | Path-based proxy via default server |
| **WAN** | `https://clipboard.tdemers.duckdns.org/` | Subdomain-based, separate `server_name` |
| **Direct** | `http://127.0.0.1:5555/` | Bypasses nginx, hits Python directly |

### How it works

1. **GET** `/` returns the HTML page with the current clipboard content pre-filled in the textarea
2. **POST** `text=...` saves the content to `/var/lib/clipboard/clipboard.txt` and redraws the page

The server listens on `127.0.0.1:5555` and is proxied behind nginx at `/clipboard/`. All storage is a plain text file — no database, no dependencies beyond Python 3.

### Design decisions

- **No auth** — open to anyone on the network (same as other LAN services)
- **No styling beyond dark theme** — functional, matches the landing page's `#1a1a2e` background
- **Full-height textarea** — uses `80vh` so most of the viewport is editable
- **Zero dependencies** — pure Python 3 `http.server` and `urllib.parse`, nothing to install
- **Subdomain + path-based** — works both as `clipboard.tdemers.duckdns.org` (clean URL) and `/clipboard/` on any local IP
- **No WebSocket or streaming** — simple request/response, no upgrade headers needed

## Lessons learned

### Path-based vs subdomain routing

Services that assume they own the domain root (`/`) produce absolute paths in HTML (CSS, JS, images). When proxied behind a sub-path like `/pihole/`, those paths break — the browser requests `/admin/...` instead of `/pihole/admin/...`.

**Path-based** (our original setup) — single `server_name`, multiple `location ^~` blocks:
- ✅ Single SSL cert, single port 443
- ✅ Works with any hostname/IP on the same nginx instance
- ❌ Requires `proxy_redirect` and `X-Forwarded-Prefix` hacks
- ❌ Broken assets when apps use absolute paths (Pi-hole, etc.)
- ❌ Must proxy every sub-path the app generates (`/pihole/` + `/admin/`)

**Subdomain-based** (new setup) — one `server_name` per service:
- ✅ Each app thinks it owns `/` — no path rewriting needed
- ✅ No broken assets, no `proxy_redirect` needed
- ✅ Cleaner, simpler location blocks
- ❌ Requires SSL cert with SANs for each subdomain
- ❌ Only works on the duckdns domain (not local IPs)
- ❌ DNS must resolve each subdomain

Bottom line: subdomains are cleaner, but path-based is needed for LAN-only access on local IPs. We run both in parallel.

### The `proxy_redirect` pattern

When an app returns a 302 redirect to its canonical external URL (e.g. Nextcloud → `https://tdemers.duckdns.org/nextcloud/login`), and that URL is unreachable from the LAN (hairpin NAT), nginx can rewrite the redirect in-flight:

```
proxy_redirect https://tdemers.duckdns.org/ http://$host/;
```

This intercepts the `Location` header in the 302 response and rewrites it before sending to the client. Without this, the browser follows the redirect to the domain, which times out from inside the LAN.

### Pi-hole behind a reverse proxy

Pi-hole has two quirks:
1. **Root `/` returns 403** — the real interface is at `/admin/`. Accessing `/pihole/` proxies to Pi-hole's root and gets a 403 with a link to `/admin/`.
2. **Absolute paths in HTML** — all CSS/JS/images use `/admin/...` paths. You must also proxy `/admin/` to Pi-hole, otherwise those assets hit Nextcloud and return 404.

The fix requires **two** location blocks:

```
location ^~ /pihole/ { proxy_pass http://10.88.0.3:80/; ... }
location ^~ /admin/  { proxy_pass http://10.88.0.3:80/admin/; ... }
```

Both must have the same IP-restriction rules.

### Nginx location matching order

Knowing the precedence saves debugging time:

| Priority | Syntax | Example | Notes |
|---|---|---|---|
| 1 (highest) | `= /path` | `location = /` | Exact match only |
| 2 | `^~ /path/` | `location ^~ /nextcloud/` | Prefix match, stops regex search |
| 3 | `~` or `~*` | `location ~ \.php$` | Regex match (first match wins) |
| 4 (lowest) | `/path/` | `location /` | Regular prefix match (longest wins) |

`^~` is critical for service prefixes — it prevents regex locations from overriding the proxy rule.

### The default server trap

Nginx has a **default server** for each port — the first `server` block that matches or has `default_server` set. On port 80, the default is defined in `nginx.conf`:

```
server {
    listen 80;
    server_name _;
    ...
    include /etc/nginx/default.d/*.conf;
}
```

If a specific `server_name` (like `192.168.0.31`) was listed in another port 80 server block, requests to that IP matched that block instead of the default. By removing `192.168.0.31` from the Certbot-managed block's `server_name`, HTTP requests to the local IP fell through to the default server — which already had all the proxy locations via `default.d/services.conf`.

### Docker/Podman networking

All containers are managed by Podman and published to localhost ports:

| Container | Internal port | Published on host |
|---|---|---|
| Pi-hole | `80` | `192.168.0.31:8089` + Docker bridge `10.88.0.3:80` |
| Nextcloud | `80` | `127.0.0.1:8080` |
| Netdata | `19999` | `127.0.0.1:19999` |
| Vaultwarden | `80` | `127.0.0.1:8222` |

When proxying to containers, use the **host-published port** (`127.0.0.1:19999`, not the container's internal IP), unless the container has a dedicated Docker bridge network IP (Pi-hole at `10.88.0.3`).