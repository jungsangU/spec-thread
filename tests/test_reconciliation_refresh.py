import json
import sys
import unittest
from copy import deepcopy

import test_lifecycle_gates as fixture
from sdd_core.records import read_document

A = fixture.A


class ReconciliationRefreshTest(unittest.TestCase):
    setUp = fixture.LifecycleGateTest.setUp
    write = fixture.LifecycleGateTest.write
    cli = fixture.LifecycleGateTest.cli
    plan = fixture.LifecycleGateTest.plan
    analyze = fixture.LifecycleGateTest.analyze
    start = fixture.LifecycleGateTest.start
    command_gate = fixture.LifecycleGateTest.command_gate
    define = fixture.LifecycleGateTest.define
    completion = fixture.LifecycleGateTest.completion

    def sync_plan(self):
        return {'base': {'kind': 'files', 'refs': ['basis.md']}, 'features': [A],
                'reason': 'Reconcile externally changed behavior after review',
                'findings': [{'assessment': 'SAFE', 'evidence': 'Reviewed code and intent'}],
                'basis': ['basis.md'], 'paths': ['app.py'],
                'changes': [{'path': 'specs/a/spec.md', 'content': '# Approved reconciled intent\n'}],
                'verification': {'reason': 'Approved test coverage', 'basis': ['basis.md'],
                                 'gates': [self.command_gate()]}}

    def preview(self, command, *args):
        code, output, error = self.cli(command, *args)
        self.assertEqual(code, 0, error)
        return json.loads(output)

    def apply_sync(self):
        path = self.plan('sync.json', self.sync_plan())
        preview = self.preview('reconcile', path)
        result = self.preview('reconcile', path, '--confirm', preview['approval_hash'])
        return result['work_item']

    def test_reconcile_preview_read_only_and_input_change_rejected(self):
        path = self.plan('sync.json', self.sync_plan())
        history = read_document(self.root, 'work-items.yaml')
        original = (self.root / 'specs/a/spec.md').read_bytes()
        preview = self.preview('reconcile', path)
        self.assertEqual(history, read_document(self.root, 'work-items.yaml'))
        self.assertEqual(original, (self.root / 'specs/a/spec.md').read_bytes())
        self.write('app.py', 'external change after approval\n')
        self.assertEqual(self.cli('reconcile', path, '--confirm', preview['approval_hash'])[0], 1)
        self.assertEqual(history, read_document(self.root, 'work-items.yaml'))

    def test_reconcile_creates_history_and_requires_real_verification(self):
        identifier = self.apply_sync()
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        self.assertEqual(item['kind'], 'reconciliation')
        self.assertEqual(item['status'], 'in_progress')
        self.assertIn('approval_hash', item['reconciliation'])
        self.assertEqual(self.cli('complete', identifier, self.completion())[0], 1)
        self.assertEqual(self.cli('gate-run', identifier, 'project-tests')[0], 0)
        self.assertEqual(self.cli('complete', identifier, self.completion())[0], 0)
        self.assertEqual(read_document(self.root, 'work-items.yaml')['work_items'][0]['status'], 'completed')
        self.assertEqual(self.cli('gate-run', identifier, 'project-tests')[0], 1)

    def test_reconcile_cannot_write_app_or_history_or_bypass_findings(self):
        for name in ['app.py', '../outside.md', '.specify/baseline/work-items.yaml']:
            plan = self.sync_plan()
            plan['changes'][0]['path'] = name
            self.assertEqual(self.cli('reconcile', self.plan('sync.json', plan))[0], 1)
        plan = self.sync_plan()
        plan['findings'][0]['assessment'] = 'UNKNOWN'
        self.assertEqual(self.cli('reconcile', self.plan('sync.json', plan))[0], 1)
        plan = self.sync_plan()
        plan['verification']['gates'] = []
        self.assertEqual(self.cli('reconcile', self.plan('sync.json', plan))[0], 1)

    def test_reconcile_plan_and_base_changes_need_reapproval(self):
        plan = self.sync_plan()
        path = self.plan('sync.json', plan)
        preview = self.preview('reconcile', path)
        plan['changes'][0]['content'] = '# Different proposal\n'
        self.plan('sync.json', plan)
        self.assertEqual(self.cli('reconcile', path, '--confirm', preview['approval_hash'])[0], 1)
        plan = self.sync_plan()
        path = self.plan('sync.json', plan)
        preview = self.preview('reconcile', path)
        self.write('basis.md', 'Changed comparison evidence\n')
        self.assertEqual(self.cli('reconcile', path, '--confirm', preview['approval_hash'])[0], 1)

    def test_reconcile_partial_failure_records_failed_without_rollback(self):
        plan = self.sync_plan()
        plan['changes'].append({'path': '.specify/baseline/source-map.yaml', 'content': 'mappings: wrong\n'})
        path = self.plan('sync.json', plan)
        approval = self.preview('reconcile', path)['approval_hash']
        result = self.cli('reconcile', path, '--confirm', approval)
        self.assertEqual(result[0], 1)
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        self.assertEqual(item['status'], 'failed')
        self.assertIn('error', item['reconciliation'])
        self.assertEqual((self.root / 'specs/a/spec.md').read_text(), '# Approved reconciled intent\n')

    def two_gates(self):
        identifier = self.start()
        a = self.command_gate()
        b = self.command_gate()
        b['id'] = 'unaffected'
        b['paths'] = ['basis.md']
        b['evidence'] = ['other-result.txt']
        b['command'] = [sys.executable, '-c', "from pathlib import Path; Path('other-result.txt').write_text('actual result')"]
        self.define(identifier, [a, b])
        self.assertEqual(self.cli('transition', identifier, 'in_progress')[0], 0)
        for gate in ['project-tests', 'unaffected']:
            self.assertEqual(self.cli('gate-run', identifier, gate)[0], 0)
        return identifier

    def refresh(self, identifier):
        preview = self.preview('gate-refresh', identifier)
        return self.preview('gate-refresh', identifier, '--confirm', preview['approval_hash'])

    def test_selective_refresh_reuses_unchanged_and_runs_only_stale(self):
        identifier = self.two_gates()
        self.write('app.py', 'value = 2\n')
        result = self.refresh(identifier)
        self.assertEqual(result['status'], 'PASS')
        actions = {x['gate']: x['action'] for x in result['results']}
        self.assertEqual(actions, {'project-tests': 'run', 'unaffected': 'reuse'})
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        self.assertEqual(len(item['gate_results']['unaffected']), 1)
        self.assertEqual(len(item['gate_results']['project-tests']), 2)

    def test_rename_requires_approval_reruns_changed_preserves_other_evidence(self):
        identifier = self.two_gates()
        (self.root / 'app.py').rename(self.root / 'renamed.py')
        before = deepcopy(read_document(self.root, 'work-items.yaml'))
        preview = self.preview('gate-refresh', identifier)
        self.assertEqual(preview['renames'], {'app.py': 'renamed.py'})
        self.assertEqual(before, read_document(self.root, 'work-items.yaml'))
        result = self.preview('gate-refresh', identifier, '--confirm', preview['approval_hash'])
        self.assertEqual(result['status'], 'PASS')
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        self.assertEqual(item['gate_revisions'][-1]['gates'][0]['paths'], ['renamed.py'])
        self.assertIn('reused_from', item['gate_results']['unaffected'][-1])
        self.assertEqual(before['work_items'][0]['gate_results']['unaffected'][0], item['gate_results']['unaffected'][0])

    def test_duplicate_rename_candidate_blocks_without_mutating_history(self):
        identifier = self.two_gates()
        (self.root / 'app.py').rename(self.root / 'one.py')
        self.write('two.py', 'value = 1\n')
        preview = self.preview('gate-refresh', identifier)
        self.assertIn('app.py', preview['ambiguous'])
        before = (self.root / '.specify/baseline/work-items.yaml').read_bytes()
        self.assertEqual(self.cli('gate-refresh', identifier, '--confirm', preview['approval_hash'])[0], 1)
        self.assertEqual(before, (self.root / '.specify/baseline/work-items.yaml').read_bytes())

    def test_refresh_approval_binds_new_candidate_and_current_files(self):
        identifier = self.two_gates()
        (self.root / 'app.py').rename(self.root / 'one.py')
        preview = self.preview('gate-refresh', identifier)
        self.write('two.py', 'value = 1\n')
        self.assertEqual(self.cli('gate-refresh', identifier, '--confirm', preview['approval_hash'])[0], 1)

    def test_refresh_does_not_invent_review_or_reopen_completed(self):
        identifier = self.start()
        gate = self.command_gate()
        gate.update(kind='review', method='Official actual review', evidence=['basis.md'])
        gate.pop('command')
        self.define(identifier, [gate])
        preview = self.preview('gate-refresh', identifier)
        result = self.cli('gate-refresh', identifier, '--confirm', preview['approval_hash'])
        self.assertEqual(result[0], 2)
        self.assertEqual(json.loads(result[1])['results'][0]['action'], 'review_required')

    def test_reconcile_binds_other_official_artifacts_and_selector(self):
        path = self.plan('sync.json', self.sync_plan())
        preview = self.preview('reconcile', path)
        self.write('specs/a/new-contract.md', 'new external contract')
        self.assertEqual(self.cli('reconcile', path, '--confirm', preview['approval_hash'])[0], 1)

    def test_reconcile_git_base_is_resolved_and_bound_to_commit(self):
        import subprocess
        for args in [('init', '-q'), ('add', '.'), ('-c', 'user.name=Fixture', '-c',
                     'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture base')]:
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True)
        plan = self.sync_plan()
        plan['base'] = {'kind': 'git', 'revision': 'HEAD'}
        preview = self.preview('reconcile', self.plan('sync.json', plan))
        self.assertEqual(len(preview['base']['commit']), 40)
        self.write('unrelated.txt', 'new commit')
        for args in [('add', 'unrelated.txt'), ('-c', 'user.name=Fixture', '-c',
                     'user.email=fixture@example.invalid', 'commit', '-qm', 'move base')]:
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True)
        self.assertEqual(self.cli('reconcile', str(self.root / 'sync.json'), '--confirm', preview['approval_hash'])[0], 1)

    def test_refresh_updates_active_source_map_after_approved_rename(self):
        identifier = self.two_gates()
        self.write('.specify/baseline/source-map.yaml', json.dumps({
            'mappings': [{'feature_id': A, 'sources': [{'path': 'app.py'}]}]}))
        (self.root / 'app.py').rename(self.root / 'new.py')
        self.assertEqual(self.refresh(identifier)['status'], 'PASS')
        source = read_document(self.root, 'source-map.yaml')['mappings'][0]['sources'][0]
        self.assertEqual(source['path'], 'new.py')

    def test_refresh_missing_file_without_candidate_blocks(self):
        identifier = self.two_gates()
        (self.root / 'app.py').unlink()
        preview = self.preview('gate-refresh', identifier)
        self.assertEqual(preview['ambiguous']['app.py'], [])
        self.assertEqual(self.cli('gate-refresh', identifier, '--confirm', preview['approval_hash'])[0], 1)

    def test_refresh_does_not_reuse_previous_pass_after_latest_failure(self):
        identifier = self.two_gates()
        gate = self.command_gate(command=[sys.executable, '-c', 'raise SystemExit(3)'])
        self.define(identifier, [gate])
        self.assertEqual(self.cli('gate-run', identifier, 'project-tests')[0], 2)
        preview = self.preview('gate-refresh', identifier)
        self.assertEqual(preview['actions'][0]['action'], 'run')
        self.assertEqual(self.cli('gate-refresh', identifier, '--confirm', preview['approval_hash'])[0], 2)

    def test_completed_work_cannot_be_refreshed(self):
        identifier = self.two_gates()
        self.assertEqual(self.cli('complete', identifier, self.completion())[0], 0)
        history = (self.root / '.specify/baseline/work-items.yaml').read_bytes()
        self.assertEqual(self.cli('gate-refresh', identifier)[0], 1)
        self.assertEqual(history, (self.root / '.specify/baseline/work-items.yaml').read_bytes())

    def test_unknown_schema_rejects_sync_before_writes(self):
        data = read_document(self.root, 'features.yaml')
        data['schema_version'] = 999
        self.write('.specify/baseline/features.yaml', json.dumps(data))
        before = (self.root / 'specs/a/spec.md').read_bytes()
        self.assertEqual(self.cli('reconcile', self.plan('sync.json', self.sync_plan()))[0], 1)
        self.assertEqual(before, (self.root / 'specs/a/spec.md').read_bytes())
        self.assertEqual(read_document(self.root, 'work-items.yaml')['work_items'], [])
