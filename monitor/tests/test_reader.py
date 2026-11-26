from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from specthread_monitor.reader import reader_response, set_reader


class ReaderTest(unittest.TestCase):
    def test_reader_enables_only_exact_queries_in_this_project(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            raw = {"cwd": str(root), "hook_event_name": "PermissionRequest", "tool_name": "Bash",
                   "tool_input": {"command": "git branch --show-current"}}
            with patch("specthread_monitor.reader.location", return_value=root / "state"), \
                    patch("sdd_core.office.location", return_value=root / "state"):
                self.assertIsNone(reader_response(root, raw))
                set_reader(root, True)
                self.assertEqual(reader_response(root, raw)["hookSpecificOutput"]["decision"]["behavior"], "allow")
                for command in ("rm app.py", "git branch -D develop", "ls && rm app.py",
                                "pwd > output", "ls ..", "python3 .specify/sdd-core gates ID plan --confirm HASH"):
                    self.assertIsNone(reader_response(root, {**raw, "tool_input": {"command": command}}))
                self.assertIsNone(reader_response(root, {**raw, "cwd": str(root.parent)}))
                with patch("specthread_monitor.reader.time.time", return_value=0):
                    self.assertIsNone(reader_response(root, raw))
                set_reader(root, False)
                self.assertIsNone(reader_response(root, raw))

    def test_ceo_grants_project_hook_requests_and_expires(self):
        from specthread_monitor.reader import set_office_role

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            raw = {"cwd": str(root), "hook_event_name": "PermissionRequest", "tool_name": "Write",
                   "tool_input": {"file_path": "app.py"}}
            with patch("specthread_monitor.reader.location", return_value=root / "state"), \
                    patch("sdd_core.office.location", return_value=root / "state"):
                self.assertIsNone(reader_response(root, raw))
                set_office_role(root, "ceo", True)
                self.assertEqual(reader_response(root, raw)["hookSpecificOutput"]["decision"]["behavior"], "allow")
                self.assertIsNone(reader_response(root, {**raw, "cwd": str(root.parent)}))
                self.assertIsNone(reader_response(root, {**raw, "hook_event_name": "PostToolUse"}))
                set_office_role(root, "ceo", False)
                self.assertIsNone(reader_response(root, raw))
