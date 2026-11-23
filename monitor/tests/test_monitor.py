import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from sdd_core.baseline import scaffold
from sdd_core.gates import execute_gate, prepare_gate_plan, register_gates
from sdd_core.records import read_document, write_document
from sdd_core.version_sync import install_skills
from specthread_monitor.events import collect
from specthread_monitor.observe import snapshot
from specthread_monitor.server import MonitorServer

FEATURE = "01951d7f-b507-7200-8000-000000000001"
WORK = "01951d7f-b507-7200-8000-000000000002"


class MonitorTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name).resolve()
        self.root = self.temp / "worktree"
        self.root.mkdir()
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, name, content):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def start_server(self):
        server = MonitorServer(self.root, [], 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        return server

    def request(self, server, path, *, signed=True, method="GET", host=None):
        headers = {"X-Monitor-Token": server.token} if signed else {}
        if host:
            headers["Host"] = host
        return urlopen(Request(f"http://{server.authority}{path}", headers=headers, method=method), timeout=5)

    def test_http_auth_assets_and_diff(self):
        self.write("app [x].py", "old\n")
        self.git("add", "--", "app [x].py")
        self.write("app [x].py", "new\n")
        server = self.start_server()
        with self.request(server, "/", signed=False) as response:
            self.assertIn(b"SpecThread Monitor", response.read())
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        with self.request(server, "/app.js", signed=False) as response:
            self.assertIn(b"createOffice", response.read())
        with self.assertRaises(HTTPError) as error:
            self.request(server, "/api/snapshot", signed=False)
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            self.request(server, "/api/snapshot", host="example.invalid")
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            self.request(server, "/api/snapshot", method="POST")
        self.assertEqual(error.exception.code, 501)
        with self.request(server, "/api/snapshot") as response:
            state = json.load(response)
        self.assertEqual(state["baseline"]["state"], "missing")
        self.assertEqual(state["git"]["files"], [{"path": "app [x].py", "status": "AM"}])
        for staged, text in (("1", "+old"), ("0", "+new")):
            query = urlencode({"path": "app [x].py", "staged": staged})
            with self.request(server, f"/api/diff?{query}") as response:
                self.assertIn(text, json.load(response)["patch"])
        with self.assertRaises(HTTPError) as error:
            self.request(server, "/api/diff?path=../outside&staged=0")
        self.assertEqual(error.exception.code, 400)

    def test_artifact_preview_is_limited_to_known_project_text(self):
        relative = "specs/session/spec.md"
        self.write(relative, "# Preview <script>literal</script>\n")
        self.write("private.txt", "unlisted")
        server = self.start_server()
        with self.request(server, "/api/artifact?" + urlencode({"path": relative})) as response:
            self.assertEqual(json.load(response), {"text": "# Preview <script>literal</script>\n", "truncated": False})
        for path in ("private.txt", "../outside"):
            with self.assertRaises(HTTPError) as error:
                self.request(server, "/api/artifact?" + urlencode({"path": path}))
            self.assertEqual(error.exception.code, 400)
        artifact = self.root / relative
        artifact.unlink()
        artifact.symlink_to(self.root / "private.txt")
        with self.assertRaises(HTTPError):
            self.request(server, "/api/artifact?" + urlencode({"path": relative}))

    def test_git_does_not_execute_repository_filter(self):
        self.write(".gitattributes", "*.txt filter=external")
        self.write("file.txt", "one\n")
        self.git("add", ".")
        self.write("file.txt", "a different byte length\n")
        self.git("config", "filter.external.clean", "touch MONITOR-MUST-NOT-RUN; cat")
        self.git("config", "filter.external.required", "true")
        self.assertEqual(snapshot(self.root)["git"]["total"], 2)
        self.assertFalse((self.root / "MONITOR-MUST-NOT-RUN").exists())

    def test_legacy_and_invalid_baseline_degrade(self):
        self.write("specs/a/tasks.md", "- [ ] item\n")
        self.write(".specify/baseline/features.yaml", "features: []\n")
        state = snapshot(self.root)
        self.assertEqual(state["baseline"]["state"], "unsupported")
        self.assertTrue(any(row["path"] == "specs/a/tasks.md" and row["present"] for row in state["artifacts"]))
        self.write(".specify/baseline/features.yaml", "not a valid: [\n")
        self.assertEqual(snapshot(self.root)["baseline"]["state"], "unavailable")

    def test_existing_core_records_gate_evidence_and_read_only(self):
        (self.root / ".specify").mkdir()
        install_skills(self.root, "codex")
        scaffold(self.root)
        self.write("specs/a/spec.md", "# Requirements\n")
        self.write("specs/a/plan.md", "# Plan\n")
        self.write("specs/a/tasks.md", "- [x] First\n- [ ] Second\n")
        data = read_document(self.root, "features.yaml")
        data["features"] = [{"id": FEATURE, "name": "Example", "status": "active",
                             "spec_path": "specs/a", "dependencies": []}]
        write_document(self.root, "features.yaml", data)
        write_document(self.root, "work-items.yaml", {"work_items": [{
            "id": WORK, "status": "in_progress", "declared_features": [FEATURE], "actual_features": []
        }]})
        plan = {"reason": "test", "basis": ["specs/a/spec.md"], "gates": [{
            "id": "project-check", "rationale": "test", "required": True,
            "required_for": ["complete"], "targets": [FEATURE], "paths": ["specs/a/plan.md"],
            "kind": "command", "evidence_requirement": "report", "evidence": ["report.txt"],
            "command": [sys.executable, "-c", "open('report.txt', 'w').write('report')"],
        }]}
        preview = prepare_gate_plan(self.root, WORK, plan)
        register_gates(self.root, WORK, preview)
        execute_gate(self.root, WORK, "project-check")
        self.git("add", ".")
        monitored = [p for p in self.root.rglob("*") if p.is_file()]
        hashes = {p: hashlib.sha256(p.read_bytes()).digest() for p in monitored}
        state = snapshot(self.root)
        self.assertEqual(state["installation"]["record_integrity"], "MATCH")
        self.assertEqual(state["baseline"]["features"][0]["tasks"], {"done": 1, "total": 2})
        self.assertEqual(state["baseline"]["items"][0]["gates"][0]["current"], "PASS")
        self.assertEqual(hashes, {p: hashlib.sha256(p.read_bytes()).digest() for p in monitored})
        self.write("specs/a/plan.md", "changed after test\n")
        state = snapshot(self.root)
        gate = state["baseline"]["items"][0]["gates"][0]
        self.assertEqual((gate["recorded"], gate["current"]), ("PASS", "STALE"))
        self.assertIn(WORK, [action["ref"] for action in state["next_actions"]])

    def test_explicit_events_and_privacy(self):
        codex = self.temp / "codex.jsonl"
        claude = self.temp / "claude.jsonl"
        codex.write_text("\n".join(map(json.dumps, [
            {"type": "thread.started", "thread_id": "codex-1"},
            {"type": "item.completed", "item": {"type": "file_change", "changes": [
                {"path": "app.py"}, {"path": "../../outside"},
            ]}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": "SECRET"}},
            {"session_id": "codex-1", "cwd": str(self.root), "hook_event_name": "PermissionRequest"},
            {"session_id": "foreign-codex", "cwd": str(self.temp), "hook_event_name": "SessionStart"},
        ])) + "\n" + '{"type":', encoding="utf-8")
        claude.write_text("\n".join(map(json.dumps, [
            {"session_id": "claude-1", "cwd": str(self.root), "hook_event_name": "PostToolUse",
             "tool_name": "Edit", "tool_input": {"file_path": str(self.root / "app.py"), "new_string": "SECRET"}},
            {"session_id": "foreign", "cwd": str(self.temp), "hook_event_name": "SessionStart"},
            {"session_id": "claude-1", "cwd": str(self.root), "hook_event_name": "PermissionRequest"},
        ])) + "\n", encoding="utf-8")
        state = collect(self.root, [("codex", codex), ("claude", claude)])
        self.assertEqual({event["session"] for event in state["events"]}, {"codex-1", "claude-1"})
        changed = [event["paths"] for event in state["events"] if event["kind"] == "file_change"]
        self.assertEqual(changed, [["app.py"], ["app.py"]])
        self.assertNotIn("SECRET", json.dumps(state))
        self.assertEqual([event["kind"] for event in state["sessions"]], ["permission_requested"] * 2)

    def test_large_codex_stream_preserves_session_context(self):
        source = self.temp / "session.jsonl"
        source.write_text(
            '{"type":"thread.started","thread_id":"large-session"}\n'
            + json.dumps({"type": "item.completed", "text": "a" * (300 * 1024)}) + "\n"
            + '{"type":"turn.completed"}\n', encoding="utf-8",
        )
        [event] = collect(self.root, [("codex", source)])["events"]
        self.assertEqual((event["session"], event["kind"]), ("large-session", "turn_completed"))

    def test_event_fifo_is_rejected_without_blocking(self):
        fifo = self.temp / "events.fifo"
        os.mkfifo(fifo)
        self.assertEqual(collect(self.root, [("codex", fifo)])["errors"], ["codex"])


if __name__ == "__main__":
    unittest.main()
