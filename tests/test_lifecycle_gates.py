import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from sdd_core.baseline import scaffold, validate
from sdd_core.cli import main
from sdd_core.records import read_document, write_document
from sdd_core.version_sync import install_skills

A = "01951d7f-b507-7200-8000-000000000001"
B = "01951d7f-b507-7200-8000-000000000002"


class LifecycleGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".specify").mkdir()
        install_skills(self.root, "codex")
        scaffold(self.root)
        self.write("basis.md", "Requirement and test selection evidence\n")
        from sdd_core.verification import empty_registry
        policy = empty_registry()
        policy.update(status='configured', reason='Explicit isolated fixture policy', basis=['basis.md'])
        write_document(self.root, 'verification.yaml', policy)
        self.write("app.py", "value = 1\n")
        for name in ("a", "b"):
            self.write(f"specs/{name}/spec.md", f"# {name}\n[Shared](../../basis.md)\n")
            self.write(f"specs/{name}/plan.md", f"# {name} plan\n")
        document = read_document(self.root, "features.yaml")
        document["features"] = [
            {"id": identifier, "name": name, "status": "active", "spec_path": f"specs/{name}", "dependencies": []}
            for identifier, name in ((A, "a"), (B, "b"))
        ]
        write_document(self.root, "features.yaml", document)
        self.discovery = {
            "mode": "greenfield", "candidate": "a",
            "checks": {name: {"status": "verified", "evidence": "basis.md"}
                       for name in ("scope", "boundaries", "requirements", "spec_quality", "workflow")},
        }
        self.analysis = {
            "status": "partial", "unanalysed": ["other subsystem"],
            "paths": ["specs/a/spec.md"], "evidence": ["specs/a/spec.md"],
            "features": {A: {"discovery": self.discovery, "dependencies": [
                {"assessment": "SAFE", "evidence": "No core dependency on unanalysed subsystem"},
            ]}},
        }

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def cli(self, *args):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def plan(self, name, data):
        self.write(name, json.dumps(data))
        return str(self.root / name)

    def analyze(self):
        result = self.cli("analysis-record", self.plan("analysis.json", self.analysis))
        self.assertEqual(result[0], 0, result[2])

    def start(self):
        self.analyze()
        result = self.cli("start", A)
        self.assertEqual(result[0], 0, result[2])
        identifier = result[1].strip()
        from verification_fixture import prepare
        prepare(self.root, identifier)
        return identifier

    def command_gate(self, stage="complete", command=None):
        return {
            "id": "project-tests", "rationale": "Project test rule covers changed implementation",
            "targets": [A], "required": True, "required_for": [stage],
            "kind": "command",
            "command": command or [sys.executable, "-c",
                                  "from pathlib import Path; Path('test-result.txt').write_text('test passed')"],
            "paths": ["app.py"], "evidence": ["test-result.txt"],
            "evidence_requirement": "Existing project's test result report",
        }

    def define(self, identifier, gates):
        config = {"reason": "Apply project test requirements", "basis": ["basis.md"], "gates": gates}
        filename = self.plan("gates.json", config)
        result = self.cli("gates", identifier, filename)
        self.assertEqual(result[0], 0, result[2])
        approval = json.loads(result[1])["approval_hash"]
        result = self.cli("gates", identifier, filename, "--confirm", approval)
        self.assertEqual(result[0], 0, result[2])

    def completion(self):
        return self.plan("complete.json", {
            "actual_features": [A],
            "findings": [{"assessment": "SAFE", "evidence": "basis.md"}],
            "evidence": [{"ref": "test-result.txt"}],
        })

    def test_not_started_rejects_start(self):
        self.assertEqual(self.cli("start", A)[0], 1)

    def test_preflight_preserves_project_files_and_existing_scope_rules(self):
        self.analyze()
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        code, output, error = self.cli("preflight", "develop", "--agent", "codex", A)
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(output)["features"], [A])
        self.assertEqual(self.cli("preflight", "develop", "--agent", "codex", B)[0], 1)
        self.assertEqual(self.cli("preflight", "init", "--agent", "codex")[0], 0)
        self.assertEqual(self.cli("preflight", "init", "--agent", "claude")[0], 1)
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_partial_ready_allows_only_confirmed_feature(self):
        self.analyze()
        self.assertEqual(self.cli("develop-check", A)[0], 0)
        self.assertEqual(self.cli("develop-check", B)[0], 1)
        self.assertEqual(self.cli("start", A)[0], 0)

    def test_blocked_and_critical_unknown_reject_entry(self):
        for assessment in ("UNKNOWN", "CONFLICT"):
            self.analysis["features"][A]["dependencies"][0]["assessment"] = assessment
            self.analyze()
            self.assertEqual(self.cli("develop-check", A)[0], 1)
        self.analysis["features"][A]["dependencies"][0]["assessment"] = "SAFE"
        self.discovery["checks"]["scope"].update(status="blocked", next_step="clarify")
        self.analyze()
        self.assertEqual(self.cli("develop-check", A)[0], 1)

    def test_analysis_input_change_invalidates_entry(self):
        self.analyze()
        self.write("specs/a/spec.md", "Changed requirement")
        self.assertEqual(self.cli("develop-check", A)[0], 1)

    def test_complete_does_not_bypass_discovery(self):
        self.analysis["status"] = "complete"
        self.analysis["unanalysed"] = []
        result = self.cli("analysis-record", self.plan("analysis.json", self.analysis))
        self.assertEqual(result[0], 1)  # B still lacks discovery evidence.

    def test_new_work_item_cannot_enter_without_gate_set(self):
        identifier = self.start()
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 1)

    def test_required_gate_pass_and_completed_history(self):
        identifier = self.start()
        self.define(identifier, [self.command_gate()])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 0)
        self.assertEqual(self.cli("complete", identifier, self.completion())[0], 1)
        result = self.cli("gate-run", identifier, "project-tests")
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(self.cli("complete", identifier, self.completion())[0], 0)
        history = read_document(self.root, "work-items.yaml")
        self.write("app.py", "value = 2\n")
        self.assertEqual(self.cli("stage-check", identifier, "complete")[0], 1)
        self.assertEqual(history, read_document(self.root, "work-items.yaml"))
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 1)

    def test_failure_stays_in_progress_and_can_rerun(self):
        identifier = self.start()
        command = [sys.executable, "-c",
                   "from pathlib import Path; import sys; "
                   "Path('test-result.txt').write_text('result'); sys.exit(0 if Path('fixed').exists() else 3)"]
        self.define(identifier, [self.command_gate(command=command)])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 0)
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 2)
        item = read_document(self.root, "work-items.yaml")["work_items"][0]
        self.assertEqual(item["status"], "in_progress")
        self.assertEqual(item["gate_results"]["project-tests"][-1]["execution"]["exit_code"], 3)
        self.write("fixed", "yes")
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 0)

    def test_missing_evidence_does_not_pass_success_command(self):
        identifier = self.start()
        self.define(identifier, [self.command_gate(command=[sys.executable, "-c", "pass"])])
        result = self.cli("gate-run", identifier, "project-tests")
        self.assertEqual(result[0], 2)
        self.assertEqual(json.loads(result[1])["status"], "FAIL")

    def test_develop_gate_prevents_transition_until_pass(self):
        identifier = self.start()
        self.define(identifier, [self.command_gate("develop")])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 1)
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 0)
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 0)
        self.write("app.py", "changed")
        self.assertEqual(self.cli("stage-check", identifier, "verify")[0], 1)  # earlier prerequisites remain required
        self.assertEqual(self.cli("stage-check", identifier, "develop")[0], 1)

    def test_gate_revision_is_approved_and_invalidates_pass(self):
        identifier = self.start()
        self.define(identifier, [self.command_gate()])
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 0)
        gate = self.command_gate()
        gate["rationale"] = "Revised project rule"
        self.define(identifier, [gate])
        self.assertEqual(self.cli("stage-check", identifier, "complete")[0], 1)
        item = read_document(self.root, "work-items.yaml")["work_items"][0]
        self.assertEqual(len(item["gate_revisions"]), 2)

    def test_failed_retry_uses_new_id_and_reference(self):
        identifier = self.start()
        self.define(identifier, [self.command_gate()])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 0)
        self.assertEqual(self.cli("transition", identifier, "failed")[0], 0)
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 1)
        result = self.cli("start", A, "--related", identifier)
        self.assertEqual(result[0], 0, result[2])
        new_id = result[1].strip()
        self.assertNotEqual(identifier, new_id)
        item = read_document(self.root, "work-items.yaml")["work_items"][-1]
        self.assertEqual(item["related_work_items"], [identifier])

    def test_archive_preserves_uuid_and_work_history_updates_links(self):
        self.write("consumer.md", "[Feature](specs/a/spec.md)")
        self.write(".specify/feature.json", json.dumps({"feature_directory": "specs/a"}))
        self.write(".specify/baseline/source-map.yaml", json.dumps({
            "mappings": [{"feature_id": A, "sources": [{"path": "app.py"}]}],
        }))
        plan = self.plan("retire.json", {
            "reason": "Merged into B", "evidence": "basis.md", "successors": [B],
            "dependency_updates": {},
        })
        result = self.cli("feature-retire", A, plan)
        self.assertEqual(result[0], 0, result[2])
        approval = json.loads(result[1])["approval_hash"]
        before = (self.root / ".specify/baseline/work-items.yaml").read_bytes()
        result = self.cli("feature-retire", A, plan, "--confirm", approval)
        self.assertEqual(result[0], 0, result[2])
        feature = read_document(self.root, "features.yaml")["features"][0]
        self.assertEqual(feature["id"], A)
        self.assertEqual(feature["status"], "retired")
        self.assertIn(f"docs/sdd/archive/{A}/spec.md", (self.root / "consumer.md").read_text())
        self.assertEqual(before, (self.root / ".specify/baseline/work-items.yaml").read_bytes())
        (self.root / "app.py").unlink()
        validate(self.root)  # retired source map may refer to historical files.
        self.assertEqual(self.cli("start", A)[0], 1)
        self.assertNotIn("feature_directory", json.loads((self.root / ".specify/feature.json").read_text()))

    def test_retirement_requires_dependency_reassessment_and_fresh_approval(self):
        document = read_document(self.root, "features.yaml")
        document["features"][1]["dependencies"] = [{"feature_id": A, "type": "api"}]
        write_document(self.root, "features.yaml", document)
        plan = {"reason": "remove", "evidence": "basis.md", "successors": [], "dependency_updates": {}}
        filename = self.plan("retire.json", plan)
        self.assertEqual(self.cli("feature-retire", A, filename)[0], 1)
        plan["dependency_updates"] = {B: []}
        filename = self.plan("retire.json", plan)
        result = self.cli("feature-retire", A, filename)
        self.assertEqual(result[0], 0, result[2])
        approval = json.loads(result[1])["approval_hash"]
        self.write("specs/a/spec.md", "changed")
        self.assertEqual(self.cli("feature-retire", A, filename, "--confirm", approval)[0], 1)

    def test_unsupported_schema_blocks_validation(self):
        document = read_document(self.root, "features.yaml")
        document["schema_version"] = 999
        write_document(self.root, "features.yaml", document)
        self.assertEqual(self.cli("validate")[0], 1)

    def test_gate_plan_preview_binds_input_and_cannot_be_reused_after_change(self):
        identifier = self.start()
        config = {"reason": "tests", "basis": ["basis.md"], "gates": [self.command_gate()]}
        filename = self.plan("gates.json", config)
        result = self.cli("gates", identifier, filename)
        self.assertEqual(result[0], 0, result[2])
        approval = json.loads(result[1])["approval_hash"]
        self.write("app.py", "modified before confirmation")
        self.assertEqual(self.cli("gates", identifier, filename, "--confirm", approval)[0], 1)
        item = read_document(self.root, "work-items.yaml")["work_items"][0]
        self.assertNotIn("gate_revisions", item)

    def test_review_gate_requires_real_evidence_and_explicit_conclusion(self):
        identifier = self.start()
        gate = {
            "id": "spec-review", "rationale": "Existing Spec Kit review",
            "targets": [A], "required": True, "required_for": ["develop"],
            "kind": "review", "method": "Review scenarios against requirements",
            "paths": ["specs/a/spec.md"], "evidence": ["basis.md"],
            "evidence_requirement": "Reviewer findings with scope and conclusion",
        }
        self.define(identifier, [gate])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 1)
        review = self.plan("review.json", {"status": "UNKNOWN", "reviewer": "Codex", "conclusion": "need evidence"})
        self.assertEqual(self.cli("gate-run", identifier, "spec-review", "--review", review)[0], 2)
        review = self.plan("review.json", {"status": "PASS", "reviewer": "Codex", "conclusion": "All listed scenarios traced"})
        self.assertEqual(self.cli("gate-run", identifier, "spec-review", "--review", review)[0], 0)
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 0)

    def test_gate_modifying_its_input_is_stale(self):
        identifier = self.start()
        command = [sys.executable, "-c",
                   "from pathlib import Path; Path('app.py').write_text('mutated'); "
                   "Path('test-result.txt').write_text('done')"]
        self.define(identifier, [self.command_gate(command=command)])
        result = self.cli("gate-run", identifier, "project-tests")
        self.assertEqual(result[0], 2)
        self.assertEqual(json.loads(result[1])["status"], "STALE")

    def test_inflight_work_prevents_retirement(self):
        self.start()
        plan = self.plan("retire.json", {"reason": "remove", "evidence": "basis.md",
                                         "successors": [], "dependency_updates": {}})
        self.assertEqual(self.cli("feature-retire", A, plan)[0], 1)

    def test_feature_register_requires_ready_and_cannot_reuse_path(self):
        plan = {
            "feature": {"name": "new", "spec_path": "specs/new", "dependencies": []},
            "discovery": deepcopy(self.discovery), "paths": ["basis.md"], "evidence": ["basis.md"],
        }
        self.write("specs/new/spec.md", "# new")
        self.write("specs/new/plan.md", "# new plan")
        filename = self.plan("register.json", plan)
        result = self.cli("feature-register", filename)
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(self.cli("feature-register", filename)[0], 1)
        self.assertEqual(self.cli("start", result[1].strip())[0], 1)  # no durable analysis yet.

    def test_archive_preserves_completed_refs_and_redirects_historical_evidence(self):
        from sdd_core.evidence import verify_evidence
        self.write("specs/a/result.txt", "past run result")
        work_id = "01951d7f-b507-7200-8000-000000000005"
        document = read_document(self.root, "work-items.yaml")
        document["work_items"] = [{
            "id": work_id, "status": "completed", "declared_features": [A], "actual_features": [A],
            "validation": {"status": "passed", "fingerprint": "sha256:" + "0" * 64,
                           "evidence": [{"ref": "specs/a/result.txt"}]},
        }]
        write_document(self.root, "work-items.yaml", document)
        before = (self.root / ".specify/baseline/work-items.yaml").read_bytes()
        original = verify_evidence(self.root, ["specs/a/result.txt"])
        plan = self.plan("retire.json", {"reason": "merge", "evidence": "basis.md",
                                         "successors": [B], "dependency_updates": {}})
        preview = self.cli("feature-retire", A, plan)
        self.assertEqual(preview[0], 0, preview[2])
        approval = json.loads(preview[1])["approval_hash"]
        result = self.cli("feature-retire", A, plan, "--confirm", approval)
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(before, (self.root / ".specify/baseline/work-items.yaml").read_bytes())
        self.assertEqual(original, verify_evidence(self.root, ["specs/a/result.txt"]))

    def test_dependency_change_invalidates_discovery(self):
        self.analyze()
        document = read_document(self.root, "features.yaml")
        document["features"][0]["dependencies"] = [{"feature_id": B, "type": "api"}]
        write_document(self.root, "features.yaml", document)
        self.assertEqual(self.cli("develop-check", A)[0], 1)

    def test_planned_new_input_is_allowed_before_development_but_required_for_execution(self):
        identifier = self.start()
        gate = self.command_gate()
        gate["paths"] = ["new-module.py"]
        self.define(identifier, [gate])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 0)
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 1)
        self.write("new-module.py", "print('new implementation')\n")
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 0)

    def test_command_cannot_rewrite_work_item_history(self):
        identifier = self.start()
        command = [sys.executable, "-c",
                   "from pathlib import Path; p=Path('.specify/baseline/work-items.yaml'); "
                   "p.write_text(p.read_text()+'tampered: true\\n')"]
        self.define(identifier, [self.command_gate(command=command)])
        self.assertEqual(self.cli("gate-run", identifier, "project-tests")[0], 1)

    def test_scope_expansion_records_reason_and_invalidates_old_gate_scope(self):
        self.analysis["paths"] = ["specs/a/spec.md", "specs/b/spec.md"]
        self.analysis["evidence"] = ["basis.md"]
        self.analysis["features"][B] = deepcopy(self.analysis["features"][A])
        identifier = self.start()
        self.define(identifier, [self.command_gate()])
        filename = self.plan("expand.json", {"features": [B], "reason": "New consumer also changes"})
        preview = self.cli("scope-expand", identifier, filename)
        self.assertEqual(preview[0], 0, preview[2])
        result = self.cli("scope-expand", identifier, filename, "--confirm", json.loads(preview[1])["approval_hash"])
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(self.cli("transition", identifier, "in_progress")[0], 1)
        item = read_document(self.root, "work-items.yaml")["work_items"][0]
        self.assertEqual(item["declared_features"], [A, B])
        self.assertEqual(item["scope_changes"][0]["reason"], "New consumer also changes")
