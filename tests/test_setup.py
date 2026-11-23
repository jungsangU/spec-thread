import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import unittest
from unittest.mock import patch

from sdd_core.setup import setup, SETUP
from sdd_core.version_sync import PROJECT, RUNNER, install_skills
from sdd_core.baseline import scaffold


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = None
        self.calls = []
        self.addCleanup(patch.stopall)
        patch('sdd_core.setup.version', return_value='1.4.0').start()
        patch('sdd_core.setup.official_state', side_effect=lambda root: self.state).start()
        patch('sdd_core.setup.official', side_effect=self.official).start()

    def official(self, root, *args, **kwargs):
        self.calls.append(args)
        (root / '.specify').mkdir(exist_ok=True)
        self.state = {'status': 'ok', 'installed_integrations': ['codex'],
                      'missing_managed_files': 0, 'modified_managed_files': 0}
        return ''

    def run_setup(self, action='install', **kwargs):
        return setup(self.root, action, 'codex', yes=True, emit=lambda value: None, **kwargs)

    def test_empty_install_and_repeat_update_need_no_json_or_manual_core_commands(self):
        self.assertEqual(self.run_setup()['status'], 'complete')
        self.assertTrue((self.root / RUNNER).is_file())
        self.assertTrue((self.root / SETUP).is_file())
        baseline = {p.name: p.read_bytes() for p in (self.root / '.specify/baseline').iterdir()}
        self.assertEqual(self.run_setup('update')['status'], 'complete')
        self.assertEqual(baseline, {p.name: p.read_bytes() for p in (self.root / '.specify/baseline').iterdir()})
        self.assertIn(('integration', 'upgrade', 'codex'), self.calls)

    def test_runner_works_from_project_without_path_or_pythonpath_setup(self):
        self.run_setup()
        import os
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        result = subprocess.run([sys.executable, str(self.root / RUNNER), 'version-check'],
                                cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_application_and_official_constitution_preserved(self):
        (self.root / 'app.py').write_text('original app\n')
        (self.root / '.specify/memory').mkdir(parents=True)
        (self.root / '.specify/memory/constitution.md').write_text('approved intent\n')
        self.state = {'status': 'ok', 'installed_integrations': ['codex']}
        self.run_setup()
        self.assertEqual((self.root / 'app.py').read_text(), 'original app\n')
        self.assertEqual((self.root / '.specify/memory/constitution.md').read_text(), 'approved intent\n')

    def test_custom_official_skill_blocks_before_any_write(self):
        (self.root / '.specify').mkdir()
        self.state = {'status': 'warning', 'installed_integrations': ['codex'], 'modified_managed_files': 1}
        with self.assertRaisesRegex(ValueError, '수정한 Spec Kit'):
            self.run_setup()
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / PROJECT).exists())

    def test_other_agent_is_not_silently_replaced(self):
        (self.root / '.specify').mkdir()
        self.state = {'status': 'ok', 'installed_integrations': ['claude']}
        with self.assertRaisesRegex(ValueError, '다른 Spec Kit'):
            self.run_setup()
        self.assertEqual(self.calls, [])

    def test_custom_harness_skill_blocks_update_before_official_writes(self):
        self.run_setup()
        self.calls.clear()
        path = self.root / '.agents/skills/sdd-init/SKILL.md'
        path.write_text('user customization')
        with self.assertRaisesRegex(ValueError, '사용자 수정'):
            self.run_setup('update')
        self.assertEqual(self.calls, [])
        self.assertEqual(path.read_text(), 'user customization')

    def test_cancel_does_not_initialize_project(self):
        result = setup(self.root, 'install', 'codex', ask=lambda _: 'n', emit=lambda _: None)
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / '.specify').exists())

    def test_mismatched_official_runtime_is_rejected(self):
        with patch('sdd_core.setup.version', return_value='0.1.6'):
            with self.assertRaisesRegex(ValueError, '1.4.0'):
                self.run_setup()
        self.assertEqual(self.calls, [])

    def test_real_project_check_is_saved_and_reused_without_reentering(self):
        (self.root / 'check.py').write_text('assert 2+2==4\n')
        command = f'{sys.executable} check.py'
        self.run_setup(check=command)
        self.run_setup('update', ask=lambda _: self.fail('should not prompt'))
        saved = json.loads((self.root / SETUP).read_text())
        self.assertEqual(saved['check'], [sys.executable, 'check.py'])

    def test_quality_failure_is_not_reported_as_success(self):
        (self.root / 'check.py').write_text('raise SystemExit(3)\n')
        with self.assertRaisesRegex(ValueError, '품질 검사'):
            self.run_setup(check=f'{sys.executable} check.py')
        settings = json.loads((self.root / SETUP).read_text())
        self.assertEqual(settings['check'], [sys.executable, 'check.py'])
        self.assertNotIn('core_version', settings)
        self.assertTrue(json.loads((self.root / PROJECT).read_text())['quality']['global_blocked'])

    def test_custom_project_runner_is_not_overwritten(self):
        self.run_setup()
        path = self.root / RUNNER
        path.write_text('user runner')
        with self.assertRaisesRegex(ValueError, '사용자 수정본'):
            self.run_setup('update')
        self.assertEqual(path.read_text(), 'user runner')

    def test_active_project_cannot_keep_initial_baseline_only_check(self):
        from sdd_core.records import read_document, write_document
        self.run_setup()
        folder = self.root / 'specs/example'
        folder.mkdir(parents=True)
        (folder / 'spec.md').write_text('# Existing spec\n')
        (folder / 'plan.md').write_text('# Existing plan\n')
        (self.root / 'check.py').write_text('assert True\n')
        data = read_document(self.root, 'features.yaml')
        data['features'] = [{'id': '01951d7f-b507-7200-8000-000000000001', 'name': 'example',
                             'status': 'active', 'spec_path': 'specs/example', 'dependencies': []}]
        write_document(self.root, 'features.yaml', data)
        prompts = []
        def answer(text):
            prompts.append(text)
            return f'{sys.executable} check.py'
        self.run_setup('update', ask=answer)
        self.assertEqual(len(prompts), 1)
        self.assertIn('테스트·빌드', prompts[0])
        self.assertEqual(json.loads((self.root / SETUP).read_text())['check'], [sys.executable, 'check.py'])

    def test_bootstrap_relays_piped_answers_to_runtime_child(self):
        import io
        import os
        import runpy
        from types import SimpleNamespace
        launcher = Path(__file__).resolve().parents[1] / 'specthread'
        module = runpy.run_path(str(launcher), run_name='test_launcher')
        def create_environment(folder):
            Path(folder).mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {'SPEC_THREAD_CACHE': str(self.root / 'cache')}), \
             patch.object(sys, 'argv', ['specthread', 'install', '--project', str(self.root), '--agent', 'codex', '--yes']), \
             patch.object(sys, 'stdin', io.StringIO('project test command\ny\n')), \
             patch('venv.EnvBuilder.create', side_effect=create_environment), \
             patch('subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(module['main'](), 0)
        self.assertEqual(run.call_args.kwargs['input'], 'project test command\ny\n')
        self.assertIn('-I', run.call_args.args[0])

    def test_user_can_change_saved_app_check_inside_same_update_command(self):
        (self.root / 'old.py').write_text('assert True\n')
        (self.root / 'new.py').write_text('assert 1 == 1\n')
        self.run_setup(check=f'{sys.executable} old.py')
        answers = iter(['c', f'{sys.executable} new.py', 'y'])
        result = setup(self.root, 'update', 'codex', ask=lambda _: next(answers), emit=lambda _: None)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(json.loads((self.root / SETUP).read_text())['check'], [sys.executable, 'new.py'])

    def test_unregistered_official_skill_is_not_forced_overwritten(self):
        folder = self.root / '.agents/skills/speckit-specify'
        folder.mkdir(parents=True)
        path = folder / 'SKILL.md'
        path.write_text('unregistered user content')
        with self.assertRaisesRegex(ValueError, '설치 기록 없는'):
            self.run_setup()
        self.assertEqual(path.read_text(), 'unregistered user content')
        self.assertEqual(self.calls, [])

    def test_retry_does_not_drop_failed_app_check_on_empty_baseline(self):
        path = self.root / 'check.py'
        path.write_text('raise SystemExit(3)\n')
        with self.assertRaisesRegex(ValueError, '품질 검사'):
            self.run_setup(check=f'{sys.executable} check.py')
        with self.assertRaisesRegex(ValueError, '품질 검사'):
            self.run_setup('update')
        path.write_text('assert 2 + 2 == 4\n')
        self.assertEqual(self.run_setup('update')['status'], 'complete')
