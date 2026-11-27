"""Actual process interleaving, not just mocked hashes."""
import multiprocessing as mp
import time
from pathlib import Path
import sys
import unittest

from sdd_core.records import read_document, write_document
from sdd_core.gates import execute_gate
from sdd_core.concurrency import project_lock
import test_verification_profiles as fixture


def execute(root, identifier, output):
    try:
        result=execute_gate(Path(root),identifier,'project-tests')
        output.put(('ok',result['status']))
    except Exception as error:
        output.put(('error',str(error)))


def edit(root, index, barrier, output):
    root=Path(root);doc=read_document(root,'work-items.yaml')
    doc['work_items'][index]['note']='process '+str(index)
    barrier.wait()
    try:write_document(root,'work-items.yaml',doc);output.put('ok')
    except Exception as e:output.put(str(e))


def hold(root,ready):
    with project_lock(Path(root)):
        ready.set();time.sleep(30)


def complete_paused(root,identifier,plan,ready,release,output):
    from unittest.mock import patch
    from sdd_core.cli import complete_work
    from sdd_core.gates import require_gates
    def pause(*args,**kwargs):
        ready.set()
        if not release.wait(10):raise ValueError('test release timeout')
        return require_gates(*args,**kwargs)
    try:
        with patch('sdd_core.cli.require_gates',side_effect=pause):complete_work(Path(root),identifier,Path(plan))
        output.put('completed')
    except Exception as error:output.put(str(error))


class ConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.f=fixture.VerificationProfilesTest('test_lightweight_minimum_and_missing_procedures_block_completion')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.root
        self.ctx=mp.get_context('spawn')

    def items(self):
        first=self.f.pending();self.f.classify(first)
        second=self.f.pending();self.f.classify(second)
        return first,second

    def test_unrelated_work_item_write_does_not_discard_running_gate(self):
        first,second=self.items()
        script="from pathlib import Path; import time; Path('ready').touch();\nwhile not Path('release').exists():time.sleep(.02)\nPath('test-result.txt').write_text('real PASS')"
        self.f.gate_set(first,[self.f.command_gate(command=[sys.executable,'-c',script])])
        output=self.ctx.Queue();p=self.ctx.Process(target=execute,args=(str(self.root),first,output));p.start()
        self.addCleanup(lambda:p.is_alive() and p.terminate())
        deadline=time.monotonic()+10
        while not(self.root/'ready').exists():
            self.assertLess(time.monotonic(),deadline);time.sleep(.02)
        doc=read_document(self.root,'work-items.yaml');doc['work_items'][1]['note']='unrelated edit'
        write_document(self.root,'work-items.yaml',doc)
        (self.root/'release').touch();p.join(10)
        self.assertEqual(output.get(timeout=1),('ok','PASS'))
        doc=read_document(self.root,'work-items.yaml')
        self.assertEqual(doc['work_items'][1]['note'],'unrelated edit')
        self.assertEqual(doc['work_items'][0]['gate_results']['project-tests'][-1]['status'],'PASS')

    def test_independent_process_record_edits_are_both_preserved(self):
        self.items();barrier=self.ctx.Barrier(2);output=self.ctx.Queue()
        processes=[self.ctx.Process(target=edit,args=(str(self.root),i,barrier,output)) for i in range(2)]
        for p in processes:p.start()
        for p in processes:p.join(10);self.assertEqual(p.exitcode,0)
        self.assertEqual([output.get(timeout=1) for _ in processes],['ok','ok'])
        doc=read_document(self.root,'work-items.yaml')
        self.assertEqual([x['note'] for x in doc['work_items']],['process 0','process 1'])

    def test_divergent_same_record_edit_is_rejected(self):
        self.items();a=read_document(self.root,'work-items.yaml');b=read_document(self.root,'work-items.yaml')
        a['work_items'][0]['note']='first';b['work_items'][0]['note']='second'
        write_document(self.root,'work-items.yaml',a)
        with self.assertRaisesRegex(ValueError,'동일 레코드'):write_document(self.root,'work-items.yaml',b)
        self.assertEqual(read_document(self.root,'work-items.yaml')['work_items'][0]['note'],'first')

    def test_kernel_releases_lock_after_owner_is_killed(self):
        ready=self.ctx.Event();p=self.ctx.Process(target=hold,args=(str(self.root),ready));p.start()
        self.assertTrue(ready.wait(10))
        with self.assertRaises(ValueError):
            with project_lock(self.root,timeout=.05):pass
        p.terminate();p.join(10)
        with project_lock(self.root,timeout=1):pass

    def test_markdown_compare_and_swap_and_source_map_record_merge(self):
        import hashlib
        from sdd_core.records import write_markdown,update_sources
        from test_lifecycle_gates import A,B
        path=self.root/'.specify/baseline/project.md';before=hashlib.sha256(path.read_bytes()).hexdigest()
        write_markdown(self.root,'project.md',before,'# First\n')
        with self.assertRaises(ValueError):write_markdown(self.root,'project.md',before,'# Second\n')
        base={'mappings':[]}
        update_sources(self.root,base,{'mappings':[{'feature_id':A,'sources':[{'path':'app.py'}]}]})
        update_sources(self.root,base,{'mappings':[{'feature_id':B,'sources':[{'path':'app.py'}]}]})
        self.assertEqual({row['feature_id'] for row in read_document(self.root,'source-map.yaml')['mappings']},{A,B})

    def test_structural_merge_uses_source_paths_and_gate_ids_not_yaml_text(self):
        from sdd_core.records import merge_changes
        base={'mappings':[]}
        one={'mappings':[{'feature_id':'feature','sources':[{'path':'one.py'}]}]}
        two={'mappings':[{'feature_id':'feature','sources':[{'path':'two.py'}]}]}
        merged=merge_changes(base,one,two)
        self.assertEqual({row['path'] for row in merged['mappings'][0]['sources']},{'one.py','two.py'})
        gates=merge_changes({'project':{'gates':[]}}, {'project':{'gates':[{'id':'a','required':True}]}}, {'project':{'gates':[{'id':'b','required':True}]}})
        self.assertEqual({gate['id'] for gate in gates['project']['gates']},{'a','b'})

    def test_completion_check_and_save_exclude_same_record_race(self):
        import threading,json
        identifier=self.f.pending();self.f.classify(identifier);self.f.procedures(identifier)
        self.assertEqual(self.f.gate_set(identifier,[self.f.command_gate()])[0],0)
        self.assertEqual(self.f.cli('transition',identifier,'in_progress')[0],0)
        self.assertEqual(self.f.cli('gate-run',identifier,'project-tests')[0],0)
        completion=self.root/'complete-race.json'
        completion.write_text(json.dumps({'actual_features':[fixture.A],'findings':[{'assessment':'SAFE','evidence':'Actual race fixture scope'}],
                                          'evidence':[{'ref':'test-result.txt'}]}))
        ready=self.ctx.Event();release=self.ctx.Event();output=self.ctx.Queue()
        owner=self.ctx.Process(target=complete_paused,args=(str(self.root),identifier,str(completion),ready,release,output))
        owner.start();self.assertTrue(ready.wait(10))
        stale=read_document(self.root,'work-items.yaml');stale['work_items'][0]['note']='stale edit after validation'
        errors=[]
        def save_stale():
            try:write_document(self.root,'work-items.yaml',stale)
            except Exception as error:errors.append(str(error))
        thread=threading.Thread(target=save_stale);thread.start()
        try:
            time.sleep(.1);self.assertTrue(thread.is_alive())
        finally:release.set();owner.join(10);thread.join(10)
        self.assertEqual(output.get(timeout=1),'completed')
        self.assertTrue(any('동일 레코드' in error for error in errors))
        item=read_document(self.root,'work-items.yaml')['work_items'][0]
        self.assertEqual(item['status'],'completed');self.assertNotIn('note',item)
