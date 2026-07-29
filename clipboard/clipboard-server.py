#!/usr/bin/env python3
"""Minimal clipboard server."""
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

DATA_FILE = "/var/lib/clipboard/clipboard.txt"
PORT = 5555
HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clipboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{display:flex;flex-direction:column;height:100vh}
textarea{flex:1;width:100%;padding:1rem;font:16px monospace;border:none;outline:none;resize:none;background:#1a1a2e;color:#e0e0e0}
button{width:100%;padding:1rem;font-size:1.2rem;border:none;background:#e94560;color:#fff;cursor:pointer}
button:hover{background:#c23152}
</style></head>
<body>
<form method="post"><textarea name="text" autofocus>{content}</textarea><button>Save</button></form>
</body></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = ""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE) as f:
                content = f.read()
        self._respond(HTML.replace("{content}", self._escape(content)))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = parse_qs(self.rfile.read(length).decode())
        text = body.get("text", [""])[0]
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            f.write(text)
        self._respond(HTML.replace("{content}", self._escape(text)))

    def _respond(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    @staticmethod
    def _escape(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
