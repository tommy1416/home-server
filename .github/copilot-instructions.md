workspace has access to the full server files directly. This repository holds documentation of a personal home server and has multiple software installed and configured. Some configuration are backed up in the git repository, for example, the real nginx configuration is located at /etc/nginx/nginx.conf and the backup is in nginx/nginx.conf.

To run commands on the home server, use `ssh server` — passwordless key auth is already set up for tdemers@192.168.0.31 (alias defined in ~/.ssh/config).

## Rules

Each time a configuration file is modified on the home server, a copy must be made in the git repository. Only copy the files if you modified them.

## Information about the home server

linux distro: Fedora 44
hardware: intel i7 9700k, AMD 290x, 1TB SSD, 4TB HDD

Softwares:
podman - not docker
Autobackup of nextcloud data from /srv/nextcloud-data to /mnt/storage/auto-backup/nextcloud
Nginx, server path: /etc/nginx/nginx.conf repo path: nginx/nginx.conf
Nextcloud
Copilot
Jellyfin
Pi-hole
Netdata
Vaultwarden
LiteLLM, server path: /etc/litellm/config.yaml repo path: litellm/config.yaml
Ollama models API (qwen2.5:1.5b, gemma3n:e4b) served behind LiteLLM proxy (port 4000 → 127.0.0.1:11434) with model aliasing (deepseek-v4-flash→qwen2.5:1.5b) and drop_params for Copilot compatibility.
Backup system from SSD to HDD
Custom clipboard

Routes:
http://192.168.0.31/
http://127.0.0.1/

Routes (Should work if we skip SSL certification validation):
https://192.168.0.31/
https://127.0.0.1/

Routes that only work from outsite (router doesn't route properly from the local network):
https://tdemers.duckdns.org/
http://tdemers.duckdns.org/

Vaultwarden, server path: /etc/systemd/system/vaultwarden.service (Podman container, port 8222)
Vaultwarden DOMAIN must be set to the subdomain URL (https://vaultwarden.tdemers.duckdns.org), not the path-based URL; routing via both /vaultwarden/ and vaultwarden. subdomain
