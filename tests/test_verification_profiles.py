import json
import sys
import unittest
from copy import deepcopy

from sdd_core.records import read_document, write_document
from sdd_core.verification import RISKS, empty_registry
import test_lifecycle_gates as fixture

A = fixture.A


class VerificationProfilesTest(unittest.TestCase):
    setUp = fixture.LifecycleGateTest.setUp
    write = fixture.LifecycleGateTest.write
    cli = fixture.LifecycleGateTest.cli
    plan = fixture.LifecycleGateTest.plan
    analyze = fixture.LifecycleGateTest.analyze
    command_gate = fixture.LifecycleGateTest.command_gate
    completion = fixture.LifecycleGateTest.completion

    def pending(self):
        self.analyze()
        code, output, error = self.cli('start', A)
        self.assertEqual(code, 0, error)
        return output.strip()

    def classification(self, **changes):
        plan = {'reason': 'Existing contract and exact changed scope reviewed', 'basis': ['basis.md'],
                'risks': {key: False for key in RISKS},
                'findings': [{'assessment': 'SAFE', 'evidence': 'Source and contract examined'}]}
        plan.update(changes)
        return plan

    def classify(self, identifier, plan=None, approve=False):
        path = self.plan('profile.json', plan or self.classification())
        if approve:
            preview = self.cli('profile', identifier, path)
            self.assertEqual(preview[0], 0, preview[2])
            return self.cli('profile', identifier, path, '--confirm', json.loads(preview[1])['approval_hash'])
        return self.cli('profile', identifier, path, '--apply')

    def gate_set(self, identifier, gates=(), compose=False, confirm=False):
        path = self.plan('gates.json', {'reason': 'Existing project coverage', 'basis': ['basis.md'], 'gates': list(gates)})
        flags = ['--compose'] if compose else []
        if confirm:
            preview = self.cli('gates', identifier, path, *flags)
            self.assertEqual(preview[0], 0, preview[2])
            return self.cli('gates', identifier, path, *flags, '--confirm', json.loads(preview[1])['approval_hash'])
        return self.cli('gates', identifier, path, *flags, '--apply')

    def procedures(self, identifier, names=('plan', 'tasks', 'implement')):
        self.write('specs/a/tasks.md', '- [x] T001 Confirm changed behavior\n')
        for name in names:
            result = self.cli('procedure', identifier, name, self.plan('procedure.json', {
                'status': 'done', 'conclusion': 'Observed fixture task and evidence', 'evidence': ['basis.md']}))
            self.assertEqual(result[0], 0, result[2])

    def catalog_gate(self, **changes):
        gate = self.command_gate()
        gate.update(profiles=['standard', 'strict'], mandatory=True, targets='$scope')
        gate.update(changes)
        policy = empty_registry()
        policy.update(status='configured', reason='Project test rule', basis=['basis.md'])
        policy['project']['gates'] = [gate]
        path = self.plan('catalog.json', policy)
        result = self.cli('verification-policy', path, '--apply')
        self.assertEqual(result[0], 0, result[2])
        return policy

    def test_lightweight_minimum_and_missing_procedures_block_completion(self):
        identifier = self.pending()
        self.assertEqual(self.classify(identifier)[0], 0)
        record = read_document(self.root, 'work-items.yaml')['work_items'][0]['verification']['revisions'][-1]
        self.assertEqual(record['profile'], 'lightweight')
        self.assertEqual(record['required_steps'], ['implement', 'plan', 'tasks'])
        self.assertEqual(self.gate_set(identifier, [self.command_gate()])[0], 0)
        self.assertEqual(self.cli('transition', identifier, 'in_progress')[0], 0)
        self.assertEqual(self.cli('gate-run', identifier, 'project-tests')[0], 0)
        self.assertEqual(self.cli('complete', identifier, self.completion())[0], 1)
        self.procedures(identifier)
        self.assertEqual(self.cli('complete', identifier, self.completion())[0], 0)

    def test_standard_new_feature_selects_discovery_and_specification(self):
        identifier = self.pending()
        plan = self.classification()
        plan['risks']['new_feature'] = True
        self.assertEqual(self.classify(identifier, plan)[0], 0)
        record = read_document(self.root, 'work-items.yaml')['work_items'][0]['verification']['revisions'][-1]
        self.assertEqual(record['profile'], 'standard')
        self.assertTrue({'discovery', 'specify'}.issubset(record['required_steps']))

    def test_strict_and_uncertainty_cannot_use_automatic_route(self):
        identifier = self.pending()
        plan = self.classification(considerations={name: {'required': False, 'reason': 'Evaluated concrete applicability'} for name in ('checklist', 'analyze', 'converge')})
        plan['risks']['auth'] = True
        self.assertEqual(self.classify(identifier, plan)[0], 1)
        self.assertNotIn('verification', read_document(self.root, 'work-items.yaml')['work_items'][0])
        self.assertEqual(self.classify(identifier, plan, approve=True)[0], 0)
        self.assertEqual(self.classify(identifier, self.classification(profile='lightweight'))[0], 1)
        other = self.pending()
        self.assertEqual(self.classify(other, self.classification(uncertain=True))[0], 1)

    def test_profile_escalation_is_monotonic_and_preserves_steps(self):
        identifier = self.pending()
        self.assertEqual(self.classify(identifier)[0], 0)
        self.procedures(identifier)
        plan = self.classification(considerations={name: {'required': name == 'analyze', 'reason': 'Contract risk evaluation'} for name in ('checklist', 'analyze', 'converge')})
        plan['risks']['migration'] = True
        self.assertEqual(self.classify(identifier, plan)[0], 1)
        self.assertEqual(self.classify(identifier, plan, approve=True)[0], 0)
        state = read_document(self.root, 'work-items.yaml')['work_items'][0]['verification']
        self.assertEqual(len(state['revisions']), 2)
        self.assertIn('analyze', state['revisions'][-1]['required_steps'])
        self.assertIn('implement', state['steps'])

    def test_critical_unknown_and_conflict_are_not_solved_by_strict(self):
        identifier = self.pending()
        for assessment in ('UNKNOWN', 'CONFLICT'):
            plan = self.classification(findings=[{'assessment': assessment, 'evidence': 'Important unresolved contract'}])
            self.assertEqual(self.classify(identifier, plan, approve=False)[0], 1)

    def test_project_mandatory_gate_cannot_be_omitted_even_with_confirm(self):
        identifier = self.pending()
        self.classify(identifier)
        self.catalog_gate()
        other = self.command_gate(); other['id'] = 'unrelated'
        self.assertEqual(self.gate_set(identifier, [other])[0], 1)
        self.assertEqual(self.gate_set(identifier, compose=True)[0], 0)
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        self.assertEqual(item['gate_revisions'][-1]['policy_sources'], {'project-tests': ['project']})

    def test_policy_weakening_requires_hash_and_invalidates_existing_set(self):
        identifier = self.pending(); self.classify(identifier)
        policy = self.catalog_gate(); self.gate_set(identifier, compose=True)
        policy['project']['gates'][0]['command'] = [sys.executable, '-c', 'raise SystemExit(3)']
        path = self.plan('changed-policy.json', policy)
        self.assertEqual(self.cli('verification-policy', path, '--apply')[0], 1)
        preview = self.cli('verification-policy', path)
        self.assertEqual(preview[0], 0, preview[2])
        self.assertEqual(self.cli('verification-policy', path, '--confirm', json.loads(preview[1])['approval_hash'])[0], 0)
        self.assertEqual(self.cli('stage-check', identifier, 'develop')[0], 1)

    def test_valid_results_reused_and_force_or_changed_input_executes(self):
        identifier = self.pending(); self.classify(identifier)
        gate = self.command_gate(command=[sys.executable, '-c', "from pathlib import Path; p=Path('runs.txt'); p.write_text(str(int(p.read_text())+1) if p.exists() else '1'); assert 'value = 1' in Path('app.py').read_text(); Path('test-result.txt').write_text('actual PASS')"])
        self.gate_set(identifier, [gate])
        self.assertEqual(self.cli('gate-run', identifier, gate['id'])[0], 0)
        again = self.cli('gate-run', identifier, gate['id'])
        self.assertEqual(json.loads(again[1])['action'], 'reuse')
        self.assertEqual((self.root / 'runs.txt').read_text(), '1')
        self.assertEqual(self.cli('gate-run', identifier, gate['id'], '--force')[0], 0)
        self.assertEqual((self.root / 'runs.txt').read_text(), '2')
        self.write('app.py', 'value = 2\n')
        self.assertEqual(self.cli('gate-run', identifier, gate['id'])[0], 2)
        self.write('app.py', 'value = 1\n')
        self.assertEqual(self.cli('gate-run', identifier, gate['id'])[0], 0)
        self.assertEqual((self.root / 'runs.txt').read_text(), '4')

    def test_other_work_item_does_not_inherit_pass(self):
        first = self.pending(); self.classify(first); self.gate_set(first, [self.command_gate()])
        self.cli('gate-run', first, 'project-tests')
        second = self.pending(); self.classify(second); self.gate_set(second, [self.command_gate()])
        self.assertEqual(self.cli('stage-check', second, 'complete')[0], 1)
        self.assertNotIn('gate_results', read_document(self.root, 'work-items.yaml')['work_items'][-1])

    def test_auto_execution_log_and_timing_are_collected_without_report_writer(self):
        identifier = self.pending(); self.classify(identifier)
        self.catalog_gate(evidence=['$execution'], command=[sys.executable, '-c', "print('actual test execution')"])
        result = self.gate_set(identifier, compose=True)
        self.assertEqual(result[0], 0, result[2])
        run = self.cli('gate-run', identifier, 'project-tests')
        self.assertEqual(run[0], 0, run[2])
        result = json.loads(run[1])
        self.assertGreater(result['execution']['duration_seconds'], 0)
        self.assertTrue(result['execution']['started_at'])
        self.assertEqual(len(result['evidence']), 1)
        self.assertIn('actual test execution', (self.root / next(iter(result['evidence']))).read_text())

    def test_unconfigured_registry_blocks_instead_of_guessing_checks(self):
        identifier = self.pending()
        write_document(self.root, 'verification.yaml', empty_registry())
        self.assertEqual(self.classify(identifier)[0], 1)

    def test_same_purpose_input_and_target_share_one_execution(self):
        identifier = self.pending(); self.classify(identifier)
        first = self.command_gate(); first['purpose'] = 'project.contract'
        second = deepcopy(first); second['id'] = 'shared-review-requirement'
        self.gate_set(identifier, [first, second])
        self.assertEqual(self.cli('gate-run', identifier, first['id'])[0], 0)
        result = self.cli('gate-run', identifier, second['id'])
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(json.loads(result[1])['reused_from']['gate'], first['id'])

    def test_suspend_resume_keeps_profile_and_valid_gate_result(self):
        identifier = self.pending(); self.classify(identifier); self.procedures(identifier)
        self.gate_set(identifier, [self.command_gate()]); self.cli('transition', identifier, 'in_progress')
        self.cli('gate-run', identifier, 'project-tests')
        self.assertEqual(self.cli('transition', identifier, 'suspended')[0], 0)
        self.assertEqual(self.cli('transition', identifier, 'in_progress')[0], 0)
        self.assertEqual(json.loads(self.cli('gate-run', identifier, 'project-tests')[1])['action'], 'reuse')

    def test_official_results_share_inputs_but_never_replace_other_purposes(self):
        first = self.pending(); self.classify(first); self.procedures(first)
        self.write('analysis-report.md', 'Actual fixture artifact comparison result')
        paths = ['specs/a/spec.md', 'specs/a/plan.md', 'specs/a/tasks.md']
        done = self.plan('official-done.json', {'status': 'done', 'conclusion': 'Cross artifact review recorded',
                                             'paths': paths, 'evidence': ['analysis-report.md']})
        self.assertEqual(self.cli('procedure', first, 'analyze', done)[0], 0)
        second = self.pending(); self.classify(second); self.procedures(second)
        plan = {'status': 'reused', 'conclusion': 'Identical purpose, inputs and report', 'paths': paths,
                'evidence': ['analysis-report.md'], 'source': {'work_item': first, 'step': 'analyze', 'index': 0}}
        reused = self.plan('official-reuse.json', plan)
        self.assertEqual(self.cli('procedure', second, 'analyze', reused)[0], 0)
        self.assertEqual(self.cli('procedure', second, 'converge', reused)[0], 1)
        self.write('analysis-report.md', 'Changed report is not the old result')
        self.assertEqual(self.cli('procedure', second, 'analyze', reused)[0], 1)

    def test_adding_gate_preserves_valid_unchanged_result_with_provenance(self):
        identifier = self.pending(); self.classify(identifier)
        gate = self.command_gate(); self.gate_set(identifier, [gate]); self.cli('gate-run', identifier, gate['id'])
        extra = deepcopy(gate); extra['id'] = 'new-check'; extra['purpose'] = 'additional-purpose'
        result = self.gate_set(identifier, [gate, extra])
        self.assertEqual(result[0], 0, result[2])
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        self.assertEqual(len(item['gate_results'][gate['id']]), 2)
        self.assertIn('reused_from', item['gate_results'][gate['id']][-1])
        self.assertNotIn('new-check', item['gate_results'])

    def test_management_updates_only_write_changed_file(self):
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (self.root / '.specify/baseline').iterdir() if path.name != 'work-items.yaml'}
        identifier = self.pending(); self.classify(identifier)
        # Analysis changes are intentional in pending(); compare after that fact is recorded.
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before}
        self.procedures(identifier); self.gate_set(identifier, [self.command_gate()])
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before})
        policy = read_document(self.root, 'verification.yaml')
        stamp = (self.root / '.specify/baseline/verification.yaml').stat().st_mtime_ns
        write_document(self.root, 'verification.yaml', policy)
        self.assertEqual(stamp, (self.root / '.specify/baseline/verification.yaml').stat().st_mtime_ns)

    def test_profile_preview_bound_to_current_work_record(self):
        identifier = self.pending()
        from sdd_core.verification import profile_preview, apply_profile
        preview = profile_preview(self.root, identifier, self.classification())
        document = read_document(self.root, 'work-items.yaml')
        document['work_items'][0]['related_work_items'] = ['some-concurrent-change']
        write_document(self.root, 'work-items.yaml', document)
        with self.assertRaisesRegex(ValueError, '변경'):
            apply_profile(self.root, identifier, preview)

    def test_required_official_review_is_invalidated_by_changed_inputs(self):
        from sdd_core.verification import steps_required
        identifier = self.pending()
        self.assertEqual(self.classify(identifier, self.classification(additional_steps=['analyze']))[0], 0)
        self.procedures(identifier)
        self.write('analysis-report.md', 'Actual review of current spec')
        plan = self.plan('review.json', {'status':'done','conclusion':'Current spec reviewed',
                                       'paths':['specs/a/spec.md'],'evidence':['analysis-report.md']})
        self.assertEqual(self.cli('procedure', identifier, 'analyze', plan)[0], 0)
        item = read_document(self.root, 'work-items.yaml')['work_items'][0]
        steps_required(self.root, item)
        self.write('specs/a/spec.md', '# Changed contract requiring another review')
        with self.assertRaises(ValueError):
            steps_required(self.root, item)
