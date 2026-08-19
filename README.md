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

## Nextcloud auto-backup

Automatic backup of all Nextcloud data from `/srv/nextcloud-data` to `/mnt/storage/auto-backup/nextcloud` on the 4TB HDD, driven by systemd timers and a bash script.

### Components

| Component | Path / Name | Purpose |
|---|---|---|
| Backup script | `/usr/local/sbin/backup-nextcloud.sh` | Performs the backup (`--monthly` = snapshot mode) |
| Daily timer | `nextcloud-backup.timer` | Runs every day at `03:15` (± 30 min random delay) |
| Daily service | `nextcloud-backup.service` | Triggers the script (oneshot) |
| Monthly timer | `nextcloud-monthly-snapshot.timer` | Runs on the 1st of each month at `04:15` |
| Monthly service | `nextcloud-monthly-snapshot.service` | Triggers the script with `--monthly` |
| Compose env | `/opt/nextcloud/.env` | `POSTGRES_*` credentials used for the DB dump |

Both services `Requires=nextcloud-compose.service`, so the backup only runs when the Nextcloud stack is up. `Persistent=true` means a missed run (e.g. server off at 03:15) is caught up on the next boot.

### Target layout

```
/mnt/storage/auto-backup/nextcloud/
├── current/                    # rolling mirror, replaced every run
│   ├── data/                   # rsync mirror of /srv/nextcloud-data
│   ├── database/nextcloud.sql  # PostgreSQL dump
│   ├── config/                 # podman-compose.yml, .env, nextcloud-config.tar.gz
│   └── completed-at.txt        # timestamp of the last completed run
├── monthly/                    # monthly snapshot (mirror of current/)
│   └── snapshot-created-at.txt
└── last-successful-run.txt     # timestamp of the last successful run
```

`current/` is a rolling mirror — each run overwrites it. `monthly/` keeps a month-end copy of the same layout.

### How it works

1. Acquires a lock (`flock` on `/run/nextcloud-backup.lock`) — if a backup is already running, the new run exits immediately (no concurrent backups).
2. Puts Nextcloud into **maintenance mode** (`occ maintenance:mode --on`); a `trap` guarantees it is switched back off when the script exits.
3. Dumps the **PostgreSQL database** → `current/database/nextcloud.sql` (written to `.new`, then atomically renamed).
4. Copies `podman-compose.yml` + `.env` → `current/config/`, plus a tarball of the Nextcloud `config/` directory.
5. **rsyncs the full data dir** `rsync -a --delete /srv/nextcloud-data/` → `current/data/` (SSD → HDD mirror).
6. Writes `current/completed-at.txt`, then `last-successful-run.txt`.
7. With `--monthly`: additionally mirrors `current/` → `monthly/` and writes `monthly/snapshot-created-at.txt`.

Because Nextcloud is in maintenance mode during the copy, the web UI briefly shows the maintenance screen — this keeps the filesystem consistent with the DB dump.

### Trigger manually

```bash
# Daily mirror backup (same as the nightly job):
sudo systemctl start nextcloud-backup.service

# Monthly snapshot (mirror + month-end copy into monthly/):
sudo systemctl start nextcloud-monthly-snapshot.service
```

Both block until finished; a large data delta can take several minutes (Nextcloud is in maintenance mode during the run).

### Verify a backup

```bash
# Last successful run (both timestamps should be freshly updated after a run):
sudo cat /mnt/storage/auto-backup/nextcloud/last-successful-run.txt
sudo cat /mnt/storage/auto-backup/nextcloud/current/completed-at.txt

# Recent runs / next scheduled run:
systemctl list-timers "nextcloud*"
journalctl -u nextcloud-backup.service -e
```

### Notes

- The data dir and backup target are root-owned (`0770` / `0750`) — you need `sudo` (or the `tape` group for `/srv/nextcloud-data`) to read them.
- The mirror is an **exact copy, not versioned** — a file deleted on the source is deleted from `current/` on the next run (`--delete`). Monthly snapshots only preserve the state at month-end.
- Backups are stored on the HDD only, not in this git repo.

### Data locations

Nextcloud runs as a Podman stack defined in `/opt/nextcloud/podman-compose.yml`.

| What | Host path | Container path | Type |
|---|---|---|---|
| **User files** (documents, photos, …) | `/srv/nextcloud-data` | `/var/www/html/data` | Bind mount |
| **Database** (PostgreSQL 16) | Podman named volume `nextcloud_db` | `/var/lib/postgresql/data` | Volume |
| **Redis cache** | Podman named volume `nextcloud_redis` | `/data` | Volume |
| **App code & config** (including `config.php`) | Podman named volume `nextcloud_html` | `/var/www/html` | Volume |

All named volumes live under `/var/lib/containers/storage/volumes/`.

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
| `/admin/` | Pi-hole web UI | `10.88.0.3:80/admin/` | LAN only — absolute `/admin/*` asset paths |
| `/api/` | Pi-hole v6 API | `10.88.0.3:80/api/` | LAN only — absolute `/api/*` calls from admin UI |
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

## Local AI / LLM (Ollama + LiteLLM)

Ollama runs local models (`qwen2.5:1.5b`, `gemma3n:e4b`) on port `11434`. A **LiteLLM proxy** (port `4000`, systemd `litellm.service`) sits in front of Ollama to handle model name aliasing and parameter filtering. Nginx exposes the OpenAI-compatible `/v1/` route on the main domain, auth-protected with the LiteLLM master key.

**How it connects to VS Code Copilot:**
The `deepseek-v4-for-copilot` extension (BYOK via VS Code LM API) is configured to point its `baseUrl` at the server and uses the LiteLLM master key as API key. The extension sends Copilot Chat requests (model `deepseek-v4-flash`, with `thinking` + `reasoning_effort` params). LiteLLM maps the model name to Ollama (`deepseek-v4-flash` → `qwen2.5:1.5b`) and drops unsupported params via `drop_params: true`.

### Architecture

```
VS Code Copilot Chat
  → deepseek-v4-for-copilot extension
    → POST https://192.168.0.31/v1/chat/completions
      → nginx (/v1/ → 127.0.0.1:4000, auth check)
        → LiteLLM proxy (model alias + drop_params)
          → Ollama (127.0.0.1:11434)
```

### Files

| File | Purpose |
|---|---|
| `/etc/systemd/system/litellm.service` | systemd unit for LiteLLM proxy |
| `/etc/litellm/config.yaml` | Model list, aliases, drop_params, master key |
| `/etc/litellm/env` | `LITELLM_MASTER_KEY` env var |
| `/etc/nginx/conf.d/ollama-auth.conf` | Bearer token check for `/v1/` |
| `/usr/local/bin/copilot-body-filter.py` | Strips `reasoning_effort` from JSON body before LiteLLM |

Backups:
- [`litellm/config.yaml`](litellm/config.yaml)

### LiteLLM model aliases

| VS Code model ID | Litellm model name | Ollama model |
|---|---|---|
| `deepseek-v4-flash` | `ollama/qwen2.5:1.5b` | `qwen2.5:1.5b` |
| `deepseek-v4-pro` | `ollama/gemma3n:e4b` | `gemma3n:e4b` |
| `qwen2.5:1.5b` | `ollama/qwen2.5:1.5b` | `qwen2.5:1.5b` |
| `gemma3n:e4b` | `ollama/gemma3n:e4b` | `gemma3n:e4b` |

### Key config: drop_params

The DeepSeek extension sends Copilot-specific parameters (`thinking`, `reasoning_effort`) that Ollama doesn't support. LiteLLM's `drop_params: true` automatically strips `thinking`, but **`reasoning_effort` requires an nginx body filter** (see `copilot-body-filter.py`) because LiteLLM v1.93.0 doesn't drop it for Ollama.

### Access

| URL | Auth | Notes |
|---|---|---|
| `https://192.168.0.31/v1/` | Bearer token | nginx checks `ollama-auth.conf`, then proxies to LiteLLM |
| `http://127.0.0.1:11434/` | None (localhost only) | Ollama directly |
| `http://127.0.0.1:4000/` | Master key | LiteLLM directly |

### Client configuration (VS Code)

```json
{
  "deepseek-copilot.baseUrl": "http://192.168.0.31/v1",
  "deepseek-copilot.apiKey": "316339f148c24563b44ab23c73696df9"
}
```

Set the API key via the `DeepSeek: Set API Key` command in VS Code.

### Ollama models

| Model | Size | Purpose |
|---|---|---|
| `qwen2.5:1.5b` | ~1 GB | Fast, general-purpose. Maps to `deepseek-v4-flash`. |
| `gemma3n:e4b` | ~2.5 GB | Reasoning-capable. Maps to `deepseek-v4-pro`. |

## Pi-hole

Runs as a **Podman container** managed by systemd (not installed directly on the host). The `pihole` command is **not** available on the host — use `podman exec` to manage it.

Service file: `/etc/systemd/system/pihole.service` (autogenerated by `podman generate systemd`)

### Deployment

```ini
ExecStart=/usr/bin/podman run \
    --name pihole \
    -p 192.168.0.31:53:53/tcp \
    -p 192.168.0.31:53:53/udp \
    -p 192.168.0.31:8089:80/tcp \
    -e TZ=America/Toronto \
    -e FTLCONF_dns_listeningMode=all \
    -e FTLCONF_dns_upstreams=1.1.1.1;9.9.9.9 \
    -v /var/lib/pihole/etc-pihole:/etc/pihole:Z pihole/pihole:latest
```

Key points:
- **DNS** listens on `192.168.0.31:53` (TCP+UDP) — bound to the LAN IP, the server's own resolver
- **Admin UI** published on `192.168.0.31:8089` (container port 80)
- Nginx proxies to the container via the Podman bridge IP **`10.88.0.3:80`** (a dedicated bridge, not `127.0.0.1` — the `-p` published port and the bridge IP are two separate ways to reach it)
- Data persists in `/var/lib/pihole/etc-pihole/`
- Uses `--rm` — removed after every stop, recreated on restart

### Access

| Route | URL | Notes |
|---|---|---|
| **Admin UI (LAN)** | `http://192.168.0.31/pihole/` | Path-based proxy, LAN only (192.168.0.0/24) |
| **Admin UI (direct)** | `http://192.168.0.31:8089/` | Published port, bypasses nginx — admin is at `/admin/` |
| **DNS** | `192.168.0.31` port `53` | Point clients here to filter DNS |
| **Nginx** | `/etc/nginx/default.d/services.conf` | `location ^~ /pihole/` → `http://10.88.0.3:80/` |

### Administration

Because `pihole` is only inside the container, run commands via `podman exec`:

```bash
# Reset the admin web password (prompts interactively)
podman exec -it pihole pihole setpassword

# View the web admin password hash
podman exec pihole pihole -a -p -s

# Restart the container
sudo systemctl restart pihole

# Follow the FTL log
podman exec pihole pihole -t
```

See "Pi-hole behind a reverse proxy" under Lessons learned for the `/admin/` asset quirk.

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

Pi-hole v6 has three quirks:
1. **Root `/` returns 403** — the real interface is at `/admin/`. Accessing `/pihole/` proxies to Pi-hole's root and gets a 403 with a link to `/admin/`.
2. **Absolute paths in HTML** — all CSS/JS/images use `/admin/...` paths. You must also proxy `/admin/` to Pi-hole, otherwise those assets hit Nextcloud and return 404.
3. **API at `/api/*` (v6)** — the admin UI (login, stats, settings) calls the API via absolute `/api/...` paths (e.g. `/api/auth`, `/api/info/login`). These must be proxied to Pi-hole too, or login breaks with "Server unreachable!" and `responseJSON is undefined` in the console.

The fix requires **three** location blocks (all with the same IP-restriction rules):

```
location ^~ /pihole/ { proxy_pass http://10.88.0.3:80/; ... }
location ^~ /admin/  { proxy_pass http://10.88.0.3:80/admin/; ... }
location ^~ /api/    { proxy_pass http://10.88.0.3:80/api/; ... }
```

⚠️ **Watch the `/api/` collision:** the Ollama endpoints `/api/models` and `/api/chat` are exact-match (`location =`), which takes precedence over the `^~ /api/` Pi-hole prefix — so they keep routing to Ollama. If the Ollama endpoints ever move to other paths, this ordering matters.


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

## Vaultwarden

Runs as a **Podman container** managed by systemd. Listens on `127.0.0.1:8222`.

Service file: `/etc/systemd/system/vaultwarden.service`

### Access

| URL | Status | Notes |
|---|---|---|
| `https://vaultwarden.tdemers.duckdns.org/` | ✅ Works (external only) | Primary access — subdomain-based routing |
| `https://tdemers.duckdns.org/vaultwarden/` | ✅ Works (external only) | Legacy path-based routing |
| `http://192.168.0.31/vaultwarden/` | ✅ Works | Local HTTP access |
| `http://127.0.0.1/vaultwarden/` | ✅ Works | Local HTTP access |

### How it works

**Two nginx routing options** exist for vaultwarden:

1. **Subdomain** (`vaultwarden.tdemers.duckdns.org`): Defined in `/etc/nginx/conf.d/subdomains.conf` — a separate server block with its own `server_name`, SSL termination, and proxy pass to `127.0.0.1:8222`.

2. **Path-based** (`/vaultwarden/`): Defined in `nextcloud.conf` inside the main SSL server block — proxied with `X-Forwarded-Prefix /vaultwarden/` so vaultwarden can generate correct relative URLs.

Both are kept in sync so either URL works.

### Deployment

```ini
ExecStart=/usr/bin/podman run \
    --name vaultwarden \
    -p 127.0.0.1:8222:80 \
    -e DOMAIN=https://vaultwarden.tdemers.duckdns.org \
    -e SIGNUPS_ALLOWED=true \
    -e WEBSOCKET_ENABLED=true \
    -v /var/lib/vaultwarden:/data:Z docker.io/vaultwarden/server:latest
```

Key points:
- **`DOMAIN`** must match the subdomain URL (`https://vaultwarden.tdemers.duckdns.org`), **not** the path-based prefix (`tdemers.duckdns.org/vaultwarden`). If set to the path-based URL, the subdomain gets a Vaultwarden 404 because it generates URLs with the wrong base path.
- Bound to `127.0.0.1:8222` — only nginx can reach it directly.
- Data persists in `/var/lib/vaultwarden/`.
- The container uses `--rm` — it's removed after every stop, then recreated on restart.

### Subdomain vs path: choosing one

Path-based routing was the original setup (single domain, path prefixes for each service). Subdomains were added later for cleaner URLs. Both still work because:
- The subdomain server block proxies `/` → `http://127.0.0.1:8222` (no prefix)
- The path-based location proxies `/vaultwarden/` → `http://127.0.0.1:8222` with `X-Forwarded-Prefix /vaultwarden/`

The `DOMAIN` env var is set to the subdomain URL, which is what vaultwarden uses to generate redirects, WebSocket URLs, and CSP headers.

## Jellyfin

Media server (Movies, Series, Music, etc.). Runs **natively as a systemd service** (not containerized) under the `jellyfin` user.

### Deployment

| Component | Path / Value | Purpose |
|---|---|---|
| systemd unit | `jellyfin.service` | Runs as user/group `jellyfin` (uid/gid 970) |
| HTTP port | `127.0.0.1:8096` | Listens internally, proxied by nginx |
| Data dir | `/var/lib/jellyfin` | Metadata, SQLite DB (`data/jellyfin.db`), user policies |
| Config dir | `/etc/jellyfin` | `system.xml`, `network.xml`, `encoding.xml` |
| Log dir | `/var/log/jellyfin` | `log_YYYYMMDD.log` + FFmpeg logs |
| Web root | `/usr/share/jellyfin-web` | Web UI served by the server |

### Access

| URL | Status | Notes |
|---|---|---|
| `https://jellyfin.tdemers.duckdns.org/` | ✅ Works (external only) | Subdomain routing via `/etc/nginx/conf.d/subdomains.conf` → `127.0.0.1:8096` |
| `http://192.168.0.31:8096/` / `http://127.0.0.1:8096/` | ✅ Works | Direct access, bypasses nginx |

### Media libraries

8 libraries, all under `/mnt/storage`: `Movies`, `Series`, `Music`, `Audio Books`, `Kids`, `Books`, `Porn`, `Games`. Library paths are stored in the SQLite DB at `/var/lib/jellyfin/data/jellyfin.db` (table `TypedBaseItems`, `type = 'CollectionFolder'`).

### File deletion permissions (fix applied 2026-07-31)

- **Symptom:** deleting a movie or song from the web UI reported an error.
- **Diagnosis:** `/var/log/jellyfin/log_20260731.log` showed `"Access to the path '/mnt/storage/Movies/...' is denied"` on `DELETE /Items/*`. The `jellyfin` process user (uid 970) had no write access because the media dirs were owned `tdemers:tdemers` with mode `755`. This was **not** a user-policy problem — the DELETE request was authorized, so the "Media Deletion" permission was already correct; the failure was purely filesystem permissions.
- **Fix:** created a shared `media` group (members `tdemers` + `jellyfin`), then for all 8 library dirs: `chgrp -R media`, `chmod -R g+rwX`, and set the **setgid** bit on directories so newly created files/folders inherit the `media` group. Finally `systemctl restart jellyfin` so the running process picks up the new group.
- **Result:** dirs are now `drwxrwsr-x tdemers:media`; `jellyfin` can read/write/delete media, `tdemers` keeps full access as owner.
- **Reusable script:** [`scripts/fix-jellyfin-perms.sh`](scripts/fix-jellyfin-perms.sh) — run with `sudo bash` if the permissions ever need to be reapplied (e.g. after a reinstall or if files are moved in without the group).