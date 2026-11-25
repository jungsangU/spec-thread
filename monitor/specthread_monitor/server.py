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
from .project_events import configured_agent, read as read_project_events

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
    if os.name == "nt":
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Artifact must be a regular file")
        with path.open("rb") as file:
            opened = os.fstat(file.fileno())
            if not os.path.samestat(before, opened) or project_path(root, name) != path:
                raise ValueError("Artifact path changed")
            return artifact_text(file.read(limit + 1), limit)
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
            return artifact_text(file.read(limit + 1), limit)


def artifact_text(text, limit):
    if b"\0" in text:
        raise ValueError("Artifact must be text")
    return {"text": text[:limit].decode("utf-8", errors="replace"), "truncated": len(text) > limit}


def session_gates(items, sessions):
    """Combine observed user-review signals with exactly linked Core gates."""
    by_id = {item["id"]: item for item in items}
    matched = {}
    attention = []
    for session in reversed(sessions):
        if session["state"] != "ended" and session.get("kind") in (
                "permission_requested", "input_requested", "turn_completed", "turn_failed", "turn_interrupted"):
            attention.append({"work": None, "agent": session["agent"], "session": session["session"],
                              "gates": [{"id": "사용자 응답·결과 확인", "status": "REVIEW"}]})
        link = session.get("gate_work") or {}
        work_id = link.get("work")
        phase = link.get("phase")
        if work_id in matched or session["state"] in ("ended", "quiet"):
            continue
        item = by_id.get(work_id)
        if not item or item["status"] in ("completed", "failed"):
            continue
        gates = [
            {"id": gate["id"], "status": gate["current"]}
            for gate in item["gates"] if gate["required"] and (
                (phase and phase in gate["stages"] and gate["current"] != "PASS")
                or (not phase and gate["current"] in ("FAIL", "UNKNOWN", "STALE"))
            )
        ]
        if not gates and item["gate_issue"]:
            gates = [{"id": "Gate 검토", "status": "REVIEW"}]
        if gates:
            matched[work_id] = {"work": work_id, "agent": session["agent"], "session": session["session"], "gates": gates}
    linked = {(row["agent"], row["session"]) for row in matched.values()}
    return list(matched.values()) + [row for row in attention if (row["agent"], row["session"]) not in linked]


class MonitorServer(HTTPServer):
    def __init__(self, root, sources, port, idle_seconds=900):
        super().__init__(("127.0.0.1", port), Handler)
        self.root = root.resolve()
        self.sources = sources
        self.idle_seconds = idle_seconds
        self.token = secrets.token_urlsafe(24)
        self.cached = None
        self.cached_at = float("-inf")

    @property
    def authority(self):
        return f"127.0.0.1:{self.server_port}"

    def get_snapshot(self):
        if time.monotonic() - self.cached_at >= 2:
            data = snapshot(self.root)
            agent = configured_agent(self.root)
            activity = collect(self.root, self.sources, read_project_events(self.root),
                               idle_seconds=self.idle_seconds, project_configured=agent is not None)
            activity["project_agent"] = agent
            activity["session_gates"] = session_gates(data["baseline"].get("items", []), activity["sessions"])
            self.cached = {**data, "activity": activity,
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


def serve_dashboard(root, sources, port, *, browser=False, idle_seconds=900):
    with MonitorServer(root, sources, port, idle_seconds) as server:
        url = f"http://{server.authority}/#token={server.token}"
        print(url, flush=True)
        agent = configured_agent(server.root)
        if agent:
            print(f'이 창을 켜 두고 같은 프로젝트의 다른 터미널에서 {agent}를 실행하세요.', flush=True)
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
    parser.add_argument("--launcher", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--record-event", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--session-idle-seconds", type=int, default=900)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--session", action="store_true")
    modes.add_argument("--dashboard-only", action="store_true")
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument("--open-browser", action="store_true")
    browser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--codex-events", action="append", type=Path, default=[])
    parser.add_argument("--claude-events", action="append", type=Path, default=[])
    args = parser.parse_args(argv)
    if args.record_event:
        from .session import record_event
        record_event()
        return 0
    if not 10 <= args.session_idle_seconds <= 86400:
        parser.error("--session-idle-seconds must be between 10 and 86400")
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
        return run_session(root, args.port, sources, browser=not args.no_browser, idle_seconds=args.session_idle_seconds)
    return serve_dashboard(root, sources, args.port,
                           browser=args.open_browser or (args.launcher and not args.no_browser),
                           idle_seconds=args.session_idle_seconds)

if __name__ == "__main__":
    raise SystemExit(main())
