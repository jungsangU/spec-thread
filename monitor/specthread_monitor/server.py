"""Local, read-only HTTP entry point. The Core never starts or calls this process."""
import argparse
import hmac
import json
import os
import secrets
import stat
import subprocess
import time
import webbrowser
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .events import collect
from .metrics import dashboard, test_report
from .observe import diff, project_path, snapshot

ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


def read_artifact(root, name, artifacts):
    if not any(row["path"] == name and row["present"] for row in artifacts):
        raise ValueError("Unknown artifact")
    path = project_path(root, name)
    if path != root / name:
        raise ValueError("Artifact must be a regular project file")
    limit = 96 * 1024
    parts = path.relative_to(root).parts
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as handles:
        parent = os.open(root, directory_flags)
        handles.callback(os.close, parent)
        for part in parts[:-1]:
            parent = os.open(part, directory_flags, dir_fd=parent)
            handles.callback(os.close, parent)
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                raise ValueError("Artifact must be a regular file")
            text = file.read(limit + 1)
    if b"\0" in text:
        raise ValueError("Artifact must be text")
    return {"text": text[:limit].decode("utf-8", errors="replace"), "truncated": len(text) > limit}


class MonitorServer(HTTPServer):
    def __init__(self, root, sources, port):
        super().__init__(("127.0.0.1", port), Handler)
        self.root = root
        self.sources = sources
        self.token = secrets.token_urlsafe(24)
        self.cached = None
        self.cached_at = float("-inf")

    @property
    def authority(self):
        return f"127.0.0.1:{self.server_port}"

    def get_snapshot(self):
        if time.monotonic() - self.cached_at >= 2:
            data = snapshot(self.root)
            self.cached = {**data, "activity": collect(self.root, self.sources),
                           "metrics": dashboard(data["baseline"], test_report(self.root))}
            self.cached_at = time.monotonic()
        return self.cached


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)
        super().setup()

    def log_message(self, *_args):
        pass

    def send_bytes(self, code, body, mime):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; "
                         "style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, data):
        self.send_bytes(code, json.dumps(data, ensure_ascii=True).encode(), "application/json")

    def do_GET(self):
        if self.headers.get("Host") != self.server.authority:
            self.send_json(403, {"error": "허용하지 않는 주소"})
            return
        try:
            url = urlsplit(self.path)
        except ValueError:
            self.send_json(400, {"error": "잘못된 주소"})
            return
        if url.path in ASSETS:
            name, mime = ASSETS[url.path]
            self.send_bytes(200, files("specthread_monitor").joinpath("ui", name).read_bytes(), mime)
            return
        supplied = self.headers.get("X-Monitor-Token", "").encode()
        if not hmac.compare_digest(supplied, self.server.token.encode()):
            self.send_json(403, {"error": "실행 시 표시된 링크를 열어 주세요"})
            return
        if url.path == "/api/snapshot":
            self.send_json(200, self.server.get_snapshot())
        elif url.path == "/api/artifact":
            try:
                query = parse_qs(url.query, max_num_fields=1, strict_parsing=True)
                name, = query["path"]
                content = read_artifact(self.server.root, name, self.server.get_snapshot()["artifacts"])
            except (ValueError, KeyError, OSError):
                self.send_json(400, {"error": "이 산출물의 텍스트를 읽을 수 없습니다"})
            else:
                self.send_json(200, content)
        elif url.path == "/api/diff":
            try:
                query = parse_qs(url.query, max_num_fields=2, strict_parsing=True)
                name, = query["path"]
                staged, = query["staged"]
                if staged not in ("0", "1"):
                    raise ValueError
                patch = diff(self.server.root, name, staged == "1")
            except (ValueError, KeyError, OSError, subprocess.TimeoutExpired):
                self.send_json(400, {"error": "선택한 변경의 diff를 읽을 수 없습니다"})
            else:
                self.send_json(200, {"patch": patch})
        else:
            self.send_json(404, {"error": "알 수 없는 경로"})


def serve_dashboard(root, sources, port, *, browser=False):
    with MonitorServer(root, sources, port) as server:
        url = f"http://{server.authority}/#token={server.token}"
        print(url, flush=True)
        if browser:
            try:
                webbrowser.open(url)
            except (OSError, webbrowser.Error):
                pass
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Open a local, read-only SpecThread dashboard")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=0)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--session", action="store_true")
    modes.add_argument("--dashboard-only", action="store_true")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--open-browser", action="store_true")
    browser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--codex-events", action="append", type=Path, default=[])
    parser.add_argument("--claude-events", action="append", type=Path, default=[])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("--root must be a directory")
    sources = [(agent, path.resolve()) for agent, paths in (
        ("codex", args.codex_events), ("claude", args.claude_events),
    ) for path in paths]
    if len(sources) + args.session > 10:
        parser.error("at most 10 event sources are supported")
    if args.session:
        from .session import run_session
        return run_session(root, args.port, sources, browser=not args.no_browser)
    return serve_dashboard(root, sources, args.port, browser=args.open_browser)

if __name__ == "__main__":
    raise SystemExit(main())
