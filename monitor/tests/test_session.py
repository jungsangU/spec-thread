from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from specthread_monitor.session import EVENT_FILE, launch_arguments, record_event, run_session


class SessionTest(unittest.TestCase):
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
