import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from sdd_core.baseline import scaffold, validate
from sdd_core.cli import main
from sdd_core.discovery import assess_discovery
from sdd_core.version_sync import install_skills


class ProductSmokeTest(unittest.TestCase):
    def test_empty_baseline_can_be_created_and_validated(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".specify").mkdir()
            scaffold(root)
            validate(root)

    def test_discovery_status_and_uuid_guard(self):
        for mode, extra in (("greenfield", "workflow"), ("brownfield", "current_behavior")):
            with self.subTest(mode=mode), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / ".specify").mkdir()
                install_skills(root, "codex")
                path = root / "plan.json"
                checks = {
                    key: {"status": "verified", "evidence": "fixture evidence"}
                    for key in ("scope", "boundaries", "requirements", "spec_quality", extra)
                }
                plan = {"mode": mode, "candidate": "test", "checks": checks}
                self.assertEqual(assess_discovery(plan)["verdict"], "READY")
                path.write_text(json.dumps(plan), encoding="utf-8")
                args = ["--root", str(root), "discovery-gate", str(path), "--issue-id"]
                with redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(args), 0)
                self.assertEqual(UUID(json.loads(output.getvalue())["feature_id"]).version, 7)
                checks[extra].update(status="condition", critical=False, next_step="verify")
                self.assertEqual(assess_discovery(plan)["verdict"], "CONDITIONAL")
                checks["requirements"].update(status="blocked", next_step="resolve conflict")
                self.assertEqual(assess_discovery(plan)["verdict"], "BLOCKED")
                path.write_text(json.dumps(plan), encoding="utf-8")
                with redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(args), 2)
                self.assertNotIn("feature_id", json.loads(output.getvalue()))
