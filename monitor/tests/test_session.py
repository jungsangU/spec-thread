from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
import time
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from specthread_monitor.events import collect, observed_gate_work
from specthread_monitor.server import MonitorServer, session_gates
from specthread_monitor.project_events import read
from specthread_monitor.session import EVENT_FILE, launch_arguments, record_event, run_session


class SessionTest(unittest.TestCase):
    def test_claude_hook_connects_to_an_already_running_dashboard(self):
        with TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            project = base / "claude-project"
            settings = project / ".claude/settings.local.json"
            settings.parent.mkdir(parents=True)
            hook = {"type": "command", "command": sys.executable,
                    "args": ["-m", "specthread_monitor.session", "--root", str(project), "--agent", "claude"]}
            settings.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [hook]}]}}))
            with patch.dict(os.environ, {"HOME": str(base), "LOCALAPPDATA": str(base)}):
                with MonitorServer(project, [], 0) as server:
                    runner = Thread(target=server.serve_forever, daemon=True)
                    runner.start()
                    request = Request(f"http://{server.authority}/api/snapshot",
                                      headers={"X-Monitor-Token": server.token})

                    def get_activity():
                        with urlopen(request, timeout=5) as response:
                            return json.load(response)["activity"]

                    try:
                        before = get_activity()
                        self.assertEqual(before["project_agent"], "claude")
                        self.assertEqual(before["sessions"], [])
                        environment = dict(os.environ)
                        module_root = Path(__file__).resolve().parents[1]
                        environment["PYTHONPATH"] = os.pathsep.join(
                            filter(None, (str(module_root), str(module_root.parent / "src"),
                                           environment.get("PYTHONPATH"))))
                        for identifier in ("later-a", "later-b"):
                            data = {"cwd": str(project), "session_id": identifier, "hook_event_name": "SessionStart"}
                            subprocess.run([hook["command"], *hook["args"]], cwd=project, env=environment,
                                           input=json.dumps(data), text=True, check=True, timeout=5)
                        deadline = time.monotonic() + 4
                        while True:
                            sessions = get_activity()["sessions"]
                            if len(sessions) == 2 or time.monotonic() >= deadline:
                                break
                            time.sleep(0.1)
                        self.assertEqual({session["session"] for session in sessions}, {"later-a", "later-b"})
                    finally:
                        server.shutdown()
                        runner.join()

    def test_gate_alert_matches_exact_session_and_current_stage(self):
        identifier = "01951d7f-b507-7200-8000-000000000002"
        command = f"python3 .specify/sdd-core stage-check {identifier} develop"
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": command}}
        observed = observed_gate_work(payload)
        self.assertEqual(observed, {"work": identifier, "phase": "develop"})
        payload["tool_input"]["command"] += " && echo ignored"
        self.assertIsNone(observed_gate_work(payload))

        item = {"id": identifier, "status": "in_progress", "gate_issue": None, "gates": [
            {"id": "entry", "current": "NOT_RUN", "required": True, "stages": ["develop", "verify", "complete"]},
            {"id": "later", "current": "NOT_RUN", "required": True, "stages": ["complete"]},
        ]}
        sessions = [
            {"session": "unrelated", "agent": "codex", "state": "working"},
            {"session": "affected", "agent": "claude", "state": "working", "gate_work": observed},
        ]
        [match] = session_gates([item], sessions)
        self.assertEqual(match["session"], "affected")
        self.assertEqual(match["gates"], [{"id": "entry", "status": "NOT_RUN"}])
        item["gates"][0]["current"] = "PASS"
        self.assertEqual(session_gates([item], sessions), [])

    def test_relay_only_writes_observation_fields(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "events.jsonl"
            path.touch()
            payload = {"cwd": str(Path.cwd()), "session_id": "abc", "hook_event_name": "PostToolUse",
                       "tool_name": "Edit", "tool_input": {"file_path": "README.md", "new_string": "SECRET"},
                       "tool_response": "private"}
            fake_input = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()))
            with patch.dict(os.environ, {EVENT_FILE: str(path), "SPECTHREAD_MONITOR_AGENT": "claude"}):
                with patch("sys.stdin", fake_input):
                    record_event()
            output = json.loads(path.read_text())
            self.assertEqual(output["tool_input"], {"file_path": "README.md"})
            self.assertNotIn("tool_response", output)

    def test_project_hooks_share_independent_sessions_and_isolate_projects(self):
        with TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            project = base / "project"
            project.mkdir()
            subfolder = project / "subfolder"
            subfolder.mkdir()
            isolated = base / "other"
            isolated.mkdir()
            nested = project / "nested"
            (nested / ".specify").mkdir(parents=True)
            (nested / ".specify/spec-thread.json").touch()
            with patch("specthread_monitor.project_events.location", side_effect=lambda root: base / "data" / root.name):
                for session, event, cwd in (
                    ("first", "UserPromptSubmit", project),
                    ("second", "SessionStart", subfolder),
                    ("second", "SessionEnd", subfolder),
                    ("foreign", "UserPromptSubmit", isolated),
                    ("nested-project", "UserPromptSubmit", nested),
                ):
                    payload = {"cwd": str(cwd), "session_id": session, "hook_event_name": event,
                               "prompt": "private prompt"}
                    fake_input = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()))
                    with patch("sys.stdin", fake_input):
                        record_event(project, "claude")
                rows = read(project)
                self.assertEqual(len(rows), 3)
                self.assertNotIn("private prompt", json.dumps(rows))
                self.assertEqual(read(isolated), [])
                state = collect(project, [], rows, idle_seconds=60)
                self.assertEqual({item["session"]: item["state"] for item in state["sessions"]},
                                 {"first": "working", "second": "ended"})
                with patch("specthread_monitor.events.time.time", return_value=time.time() + 61):
                    state = collect(project, [], rows, idle_seconds=60)
                self.assertEqual(state["sessions"][0]["state"], "quiet")

    def test_claude_settings_supply_hooks_without_policy_override(self):
        cli, flag, settings = launch_arguments("claude", "claude")
        self.assertEqual((cli, flag), ("claude", "--settings"))
        self.assertEqual(set(json.loads(settings)), {"hooks"})
        self.assertIn("SessionStart", json.loads(settings)["hooks"])

    def test_explicit_session_shares_running_monitor_and_cleans_up(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".specify").mkdir()
            (root / ".specify/spec-thread.json").write_text('{"agent":"codex"}')
            output = io.StringIO()
            event_path = None

            def fake_cli(args, *, cwd, env):
                nonlocal event_path
                self.assertEqual(args, ["/fake/codex"])
                self.assertEqual(cwd, root)
                event_path = Path(env[EVENT_FILE])
                event_path.write_text(json.dumps({"cwd": str(root), "session_id": "demo",
                                                 "hook_event_name": "SessionStart"}) + "\n")
                url = urlsplit(output.getvalue().splitlines()[0].split()[-1])
                request = Request(f"http://{url.netloc}/api/snapshot",
                                  headers={"X-Monitor-Token": url.fragment.removeprefix("token=")})
                with urlopen(request, timeout=5) as response:
                    [session] = json.load(response)["activity"]["sessions"]
                self.assertEqual(session["session"], "demo")
                return 0

            with redirect_stdout(output), patch("specthread_monitor.session.shutil.which", return_value="/fake/codex"):
                with patch("specthread_monitor.session.subprocess.call", side_effect=fake_cli):
                    self.assertEqual(run_session(root, 0, [], browser=False), 0)
            self.assertIsNotNone(event_path)
            self.assertFalse(event_path.exists())
