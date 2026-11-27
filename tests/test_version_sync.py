import io
import json
import sys
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sdd_core import __version__
from sdd_core.baseline import scaffold
from sdd_core.cli import main
from sdd_core.version_sync import PROJECT, digest, install_skills, skill_path

A = "01951d7f-b507-7200-8000-000000000001"
B = "01951d7f-b507-7200-8000-000000000002"
C = "01951d7f-b507-7200-8000-000000000003"


class VersionSyncTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / ".specify").mkdir()

    def write(self, name, data):
        file = self.root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data, encoding="utf-8")

    def cli(self, *args):
        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            code = main(["--root", str(self.root), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def fixture(self, checks):
        scaffold(self.root)
        features = []
        for identifier, name, dependencies in ((A, "a", []), (B, "b", [A]), (C, "c", [])):
            directory = f"specs/{name}"
            features.append({"id": identifier, "name": name, "spec_path": directory,
                             "dependencies": [{"feature_id": dep, "type": "api"} for dep in dependencies]})
            self.write(f"{directory}/spec.md", name)
            self.write(f"{directory}/plan.md", name)
        self.write("app.py", "print('unchanged')\n")
        self.write(".specify/baseline/features.yaml", json.dumps({"features": features}))
        self.write(".specify/baseline/source-map.yaml", json.dumps({
            "mappings": [{"feature_id": A, "sources": [{"path": "app.py", "symbol": "app"}]}],
        }))
        self.write("plan.json", json.dumps({
            "agent": "codex", "from_version": "0.1.0",
            "quality": [{"features": scope, "paths": ["app.py"],
                         "command": [sys.executable, "-c", command]} for scope, command in checks],
        }))
        return str(self.root / "plan.json")

    def preview(self, filename):
        code, out, error = self.cli("version-sync", filename)
        self.assertEqual(code, 0, error)
        return json.loads(out)["approval_hash"]

    def test_package_and_runtime_versions_agree(self):
        path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        self.assertEqual(tomllib.loads(path.read_text())["project"]["version"], __version__)

    def test_new_install_checks_actual_skill_and_enforces_agent(self):
        install_skills(self.root, "claude")
        self.assertEqual(self.cli("version-check", "--agent", "claude")[0], 0)
        self.assertEqual(self.cli("version-check", "--agent", "codex")[0], 1)
        self.write(skill_path("claude", "sdd-init"), "changed")
        self.assertEqual(self.cli("version-check", "--agent", "claude")[0], 1)

    def test_plan_is_read_only_and_approval_binds_input(self):
        filename = self.fixture([([], "pass")])
        approval = self.preview(filename)
        self.assertFalse((self.root / PROJECT).exists())
        self.write("app.py", "changed")
        self.assertEqual(self.cli("version-sync", filename, "--confirm", approval)[0], 1)
        self.assertFalse((self.root / PROJECT).exists())

    def test_legacy_metadata_and_skill_are_migrated_only_on_approval(self):
        filename = self.fixture([([], "pass")])
        retired = skill_path("codex", "sdd-commit")
        self.write(retired, "retired legacy")
        with patch.dict("sdd_core.version_sync.LEGACY_HASHES", {"sdd-commit": {digest(b"retired legacy")}}):
            approval = self.preview(filename)
            code, result, error = self.cli("version-sync", filename, "--confirm", approval)
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(result)["quality"], "passed")
        self.assertFalse((self.root / retired).exists())
        self.assertEqual((self.root / "app.py").read_text(), "print('unchanged')\n")
        self.assertNotIn("symbol", (self.root / ".specify/baseline/source-map.yaml").read_text())
        self.assertEqual(self.cli("version-check")[0], 0)

    def test_quality_failure_restricts_dependents_and_keeps_unaffected_scope_open(self):
        filename = self.fixture([([A], "raise SystemExit(1)"), ([B, C], "pass")])
        code, result, error = self.cli("version-sync", filename, "--confirm", self.preview(filename))
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(result)["restricted_features"], [A, B])
        self.assertEqual(self.cli("start", B)[0], 1)
        self.assertEqual(self.cli("version-check", C)[0], 0)
        # Migration does not invent Discovery/analysis evidence.
        self.assertEqual(self.cli("start", C)[0], 1)
        self.assertEqual(self.cli("version-check")[0], 1)

    def test_global_quality_failure_blocks_project(self):
        filename = self.fixture([([], "raise SystemExit(1)")])
        code, result, _ = self.cli("version-sync", filename, "--confirm", self.preview(filename))
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(result)["quality"], "blocked")
        self.assertEqual(self.cli("version-check", C)[0], 1)

    def test_quality_changes_input_and_does_not_finalize_migration(self):
        filename = self.fixture([([], "from pathlib import Path; Path('app.py').write_text('changed')")])
        approval = self.preview(filename)
        self.assertEqual(self.cli("version-sync", filename, "--confirm", approval)[0], 1)
        self.assertFalse((self.root / PROJECT).exists())

    def test_unsupported_migration_is_rejected_without_changes(self):
        filename = self.fixture([([], "pass")])
        self.write(PROJECT, json.dumps({"agent": "codex", "core_version": "9.0.0"}))
        config = json.loads(Path(filename).read_text())
        config.pop("from_version")
        self.write("plan.json", json.dumps(config))
        self.assertEqual(self.cli("version-sync", filename)[0], 1)
        self.assertFalse((self.root / skill_path("codex", "sdd-init")).exists())

    def test_v02_to_v03_migration_preserves_completed_history_and_requires_new_analysis(self):
        from sdd_core.records import read_document
        filename = self.fixture([([], "pass")])
        self.write(PROJECT, json.dumps({"agent": "codex", "core_version": "0.2.0",
                                      "quality": {"global_blocked": False, "restricted_features": []}}))
        config = json.loads(Path(filename).read_text())
        config.pop("from_version")
        self.write("plan.json", json.dumps(config))
        history_file = self.root / ".specify/baseline/work-items.yaml"
        history = history_file.read_bytes()
        approval = self.preview(filename)
        result = self.cli("version-sync", filename, "--confirm", approval)
        self.assertEqual(result[0], 0, result[2])
        document = read_document(self.root, "features.yaml")
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["analysis"]["status"], "not_started")
        self.assertEqual({row["id"] for row in document["features"]}, {A, B, C})
        self.assertEqual(history_file.read_bytes(), history)
        self.assertEqual(self.cli("develop-check", A)[0], 1)

    def test_unknown_schema_blocks_sync_even_when_core_path_exists(self):
        filename = self.fixture([([], "pass")])
        path = self.root / ".specify/baseline/features.yaml"
        data = json.loads(path.read_text())
        data["schema_version"] = 999
        path.write_text(json.dumps(data))
        self.assertEqual(self.cli("version-sync", filename)[0], 1)
        self.assertFalse((self.root / PROJECT).exists())

    def test_v03_to_v04_preserves_baseline_and_history(self):
        from sdd_core.version_sync import skill_marker
        install_skills(self.root, 'codex')
        scaffold(self.root)
        project = json.loads((self.root / PROJECT).read_text())
        project['core_version'] = '0.3.0'
        self.write(PROJECT, json.dumps(project))
        marker = json.loads((self.root / skill_marker('codex')).read_text())
        marker['core_version'] = '0.3.0'
        self.write(skill_marker('codex'), json.dumps(marker))
        before = {p.name: p.read_bytes() for p in (self.root / '.specify/baseline').iterdir()}
        self.write('verify.txt', 'unchanged input')
        filename = str(self.root / 'upgrade.json')
        self.write('upgrade.json', json.dumps({'agent': 'codex', 'quality': [
            {'features': [], 'paths': ['verify.txt'], 'command': [sys.executable, '-c', 'pass']}]}))
        preview = self.preview(filename)
        result = self.cli('version-sync', filename, '--confirm', preview)
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / '.specify/baseline').iterdir()})
        self.assertEqual(self.cli('version-check')[0], 0)

    def test_v04_adds_unconfigured_verification_without_rewriting_history_or_app(self):
        from sdd_core.records import write_document, read_document
        from sdd_core.version_sync import skill_marker
        install_skills(self.root, 'codex'); scaffold(self.root)
        self.write('basis.md', 'Actual structural migration fixture')
        self.write('app.py', 'value = 1\n')
        write_document(self.root, 'work-items.yaml', {'work_items': [{'id': A, 'status': 'failed', 'declared_features': [], 'actual_features': []}]})
        history = (self.root / '.specify/baseline/work-items.yaml').read_bytes()
        project = json.loads((self.root / PROJECT).read_text())
        project['core_version'] = '0.4.0'; self.write(PROJECT, json.dumps(project))
        marker = skill_marker('codex'); record = json.loads((self.root / marker).read_text())
        record['core_version'] = '0.4.0'; self.write(marker, json.dumps(record))
        (self.root / '.specify/baseline/verification.yaml').unlink()
        config = {'agent': 'codex', 'quality': [{'features': [], 'paths': ['basis.md'],
                  'command': [sys.executable, str(self.root / '.specify/sdd-core'), 'validate']}]}
        self.write('sync-v04.json', json.dumps(config))
        preview = self.cli('version-sync', str(self.root / 'sync-v04.json'))
        self.assertEqual(preview[0], 0, preview[2])
        plan = json.loads(preview[1])
        self.assertIn('risk-profiles-and-reusable-verification', [step['migration'] for step in plan['migrations']])
        result = self.cli('version-sync', str(self.root / 'sync-v04.json'), '--confirm', plan['approval_hash'])
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(read_document(self.root, 'verification.yaml')['status'], 'unconfigured')
        self.assertEqual((self.root / '.specify/baseline/work-items.yaml').read_bytes(), history)
        self.assertEqual((self.root / 'app.py').read_text(), 'value = 1\n')

    def test_v05_policy_patch_keeps_every_baseline_byte_and_requires_version_match(self):
        from sdd_core.version_sync import skill_marker
        install_skills(self.root, 'codex'); scaffold(self.root)
        self.write('quality-input.txt', 'Existing test input\n')
        before = {p.name:p.read_bytes() for p in (self.root/'.specify/baseline').iterdir()}
        project=json.loads((self.root/PROJECT).read_text());project['core_version']='0.5.0'
        self.write(PROJECT,json.dumps(project))
        marker=skill_marker('codex');record=json.loads((self.root/marker).read_text());record['core_version']='0.5.0'
        self.write(marker,json.dumps(record))
        self.assertEqual(self.cli('version-check')[0],1)
        path=str(self.root/'policy-patch.json')
        self.write('policy-patch.json',json.dumps({'agent':'codex','quality':[
            {'features':[],'paths':['quality-input.txt'],'command':[sys.executable,'-c','pass']}]}))
        preview=json.loads(self.cli('version-sync',path)[1])
        self.assertIn({'from':'0.5.0','to':'0.5.1','migration':'scoped-development-skill-policy'},preview['migrations'])
        self.assertEqual(self.cli('version-sync',path,'--confirm',preview['approval_hash'])[0],0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'.specify/baseline').iterdir()})
        self.assertEqual(self.cli('version-check')[0],0)
