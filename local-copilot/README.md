# Local Copilot

Small static chat interface for the Ollama service running on the server.

## Current integration contract

- Default model: `gemma3n:e4b`
- Other installed model: `qwen2.5:1.5b`
- Ollama listens locally on `127.0.0.1:11434`
- Ollama exposes an OpenAI-compatible route at `/v1`
- The browser calls same-origin `POST /api/chat`
- The live page is served at `https://tdemers.duckdns.org/copilot/`
- Nginx must proxy `/api/chat` to Ollama's `/v1/chat/completions`

The frontend currently expects the normal OpenAI-compatible response at `choices[0].message.content`. It also accepts Ollama's native `message.content` shape, which keeps the page tolerant of a direct Ollama proxy.

## Nginx deployment

The current HTTPS server proxies `/` to the existing Nextcloud service on `127.0.0.1:8080`. The chat files are served from `/srv/local-copilot/` through a dedicated `/copilot/` location, preserving the existing root site. On SELinux-enabled systems, apply the `httpd_sys_content_t` context to that directory.

Add the API location from `nginx-api-chat.conf` to the HTTPS server block, preserving the existing authenticated `/v1/` route:

```nginx
location = /api/chat {
    proxy_pass http://127.0.0.1:11434/v1/chat/completions;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1;
    proxy_set_header Origin "";
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_read_timeout 120s;
}
```

Run `sudo nginx -t` before `sudo systemctl reload nginx`. Verify the proxy with a POST request before opening the page in a browser.

For the static files on this server, the deployment commands are:

```bash
sudo install -d -m 755 /srv/local-copilot
sudo install -m 644 index.html styles.css app.js /srv/local-copilot/
sudo chcon -R -t httpd_sys_content_t /srv/local-copilot
```

The API route should remain same-origin. This route intentionally bypasses LiteLLM because the current LiteLLM service requires a server-side API key; add an appropriate Nginx rate limit before exposing it publicly. Do not put server credentials or API keys in the static files.