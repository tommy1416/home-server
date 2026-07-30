workspace has access to the full server files directly. This repository holds documentation of a personal home server and has multiple software installed and configured. Some configuration are backed up in the git repository, for example, the real nginx configuration is located at /etc/nginx/nginx.conf and the backup is in nginx/nginx.conf.

## Rules

Each time a configuration file is modified on the home server, a copy must be made in the git repository. Only copy the files if you modified them.

## Information about the home server

linux distro: Fedora 44
hardware: intel i7 9700k, AMD 290x, 1TB SSD, 4TB HDD

Softwares:
Nginx, server path: /etc/nginx/nginx.conf repo path: nginx/nginx.conf
Nextcloud
Copilot
Jellyfin
Pi-hole
Netdata
Vaultwarden
Ollama models API
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
