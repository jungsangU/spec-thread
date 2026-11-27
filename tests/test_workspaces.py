import json
from pathlib import Path
import shutil
import unittest

import test_verification_profiles as fixture
from sdd_core import workspaces as ws
from sdd_core.evidence import content_hash
from sdd_core.records import read_document


def crash_publication(root,identifier,plan,point):
    import os
    from unittest.mock import patch
    root=Path(root)
    original=ws.publish
    def publish(*args,**kwargs):
        def fault(index):
            journal=ws.load(ws.runtime_path(root)/'transaction.json')
            target=point if point>=0 else len(journal['actions'])-1
            if index==target:os._exit(73)
        return original(*args,**kwargs,fault=fault)
    with patch('sdd_core.workspaces.publish',side_effect=publish):ws.integrate(root,identifier,plan)


def own_lock(root,name,ready):
    import time
    with ws.project_lock(Path(root),name):
        ready.set()
        while True:time.sleep(.05)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.f=fixture.VerificationProfilesTest('test_lightweight_minimum_and_missing_procedures_block_completion')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.origin=self.f.root
        self.addCleanup(lambda:shutil.rmtree(ws.runtime_path(self.origin),ignore_errors=True))
        self.f.analyze();ws.mode(self.origin,'isolated')
        code,out,error=self.f.cli('start',fixture.A)
        self.assertEqual(code,0,error)
        info=json.loads(out);self.id=info['work_item'];self.root=Path(info['workspace'])

    def enter(self):
        (self.root/'entry.md').write_text('Explicit simulated adapter observations for Core fixture, not a native agent PoC')
        return ws.enter(self.origin,self.id,{'agent':'codex','session':__import__('os').environ.get('CODEX_THREAD_ID','fixture'),'evidence':['entry.md'],
            'checks':{k:True for k in ('same_session','absolute_edit_target','command_cwd','sandbox_access','origin_write_guard','hook_origin_link')},
            'execution':{'external_resources':'none','ports':'dynamic','relocatable':True}})

    def prepare(self):
        self.enter();self.f.root=self.root
        self.f.classify(self.id);self.f.procedures(self.id)
        gate=self.f.command_gate()
        self.assertEqual(self.f.gate_set(self.id,[gate])[0],0)
        self.assertEqual(self.f.cli('transition',self.id,'in_progress')[0],0)
        self.assertEqual(self.f.cli('gate-run',self.id,'project-tests')[0],0)
        return {'actual_features':[fixture.A],'findings':[{'assessment':'SAFE','evidence':'Explicit bounded Core fixture impact checked'}],
                'evidence':[{'ref':'test-result.txt'}]}

    def test_snapshot_is_content_not_only_manifest_and_files_are_independent(self):
        row=ws.registry(self.origin)['items'][self.id]
        self.assertEqual((Path(row['snapshot'])/'app.py').read_text(),(self.root/'app.py').read_text())
        self.assertNotEqual((self.origin/'app.py').stat().st_ino,(self.root/'app.py').stat().st_ino)
        (self.root/'app.py').write_text('value = 2\n')
        self.assertEqual((self.origin/'app.py').read_text(),'value = 1\n')
        self.assertFalse((self.root/'.git').exists())

    def test_unverified_entry_and_original_direct_edits_blocked(self):
        self.assertEqual(self.f.cli('transition',self.id,'in_progress')[0],1)
        with self.assertRaises(ValueError):ws.enter(self.origin,self.id,{'agent':'claude','checks':{}})
        with self.assertRaises(ValueError):ws.mode(self.origin,'direct')
        ws.guard(self.origin,'status')
        with self.assertRaises(ValueError):ws.guard(self.origin,'profile',self.id)

    def test_text_merge_keeps_independent_edits_and_rejects_overlap_binary(self):
        self.assertEqual(ws.text_merge(b'a\nb\nc\n',b'A\nb\nc\n',b'a\nb\nC\n'),b'A\nb\nC\n')
        with self.assertRaises(ValueError):ws.text_merge(b'a\n',b'b\n',b'c\n')
        with self.assertRaises(ValueError):ws.text_merge(b'\0a',b'\0b',b'\0c')

    def test_fifo_is_registration_order_not_start_order(self):
        self.prepare()
        self.f.root=self.origin
        code,out,error=self.f.cli('start',fixture.A);self.assertEqual(code,0,error)
        other=json.loads(out);second=other['work_item'];second_root=Path(other['workspace'])
        first_id,first_root=self.id,self.root
        self.id,self.root=second,second_root
        self.prepare()
        self.assertEqual(ws.queue(self.origin,second)['position'],1)
        self.assertEqual(ws.queue(self.origin,first_id)['position'],2)
        self.id,self.root=first_id,first_root

    def test_reviewed_integration_completes_and_retains_published_evidence(self):
        completion=self.prepare()
        result=ws.integrate(self.origin,self.id)
        self.assertEqual(result['status'],'blocked')
        result=ws.integrate(self.origin,self.id,{'preview':content_hash(result['preview']),
            'findings':completion['findings'],'completion':completion})
        self.assertEqual(result['status'],'integrated')
        self.assertEqual(read_document(self.origin,'work-items.yaml')['work_items'][0]['status'],'completed')
        self.assertTrue((self.origin/'test-result.txt').is_file())
        self.assertFalse(self.root.exists())

    def test_partial_publication_recovers_and_external_edits_are_not_overwritten(self):
        self.enter();(self.root/'app.py').write_text('value = 2\n');(self.root/'new.txt').write_text('new')
        preview=ws.candidate(self.origin,self.id)
        def fail(index):raise RuntimeError('fault injection')
        with ws.project_lock(self.origin,'integration'):
            with self.assertRaises(RuntimeError):ws.publish(self.origin,self.id,preview['source'],fault=fail)
        self.assertEqual(ws.recover(self.origin)['status'],'recovered')
        self.assertEqual((self.origin/'app.py').read_text(),'value = 1\n')
        preview=ws.candidate(self.origin,self.id)
        with self.assertRaises(RuntimeError):ws.publish(self.origin,self.id,preview['source'],fault=fail)
        (self.origin/'app.py').write_text('external user change')
        with self.assertRaisesRegex(ValueError,'외부 변경'):ws.recover(self.origin)
        self.assertEqual((self.origin/'app.py').read_text(),'external user change')

    def test_normal_copy_fallback_and_symlink_escape(self):
        from unittest.mock import patch
        target=self.root/'copy.py'
        with patch('sdd_core.workspaces.sys_platform',return_value='unsupported'):
            self.assertEqual(ws.clone_file(self.origin/'app.py',target),'copy')
        self.assertNotEqual(target.stat().st_ino,(self.origin/'app.py').stat().st_ino)
        (self.root/'escape').symlink_to(self.origin/'app.py')
        with self.assertRaises(ValueError):ws.tree(self.root)

    def test_discard_preserves_history_evidence_and_unblocks_mode_change(self):
        self.prepare()
        preview=ws.discard(self.origin,self.id,None)
        result=ws.discard(self.origin,self.id,preview['approval_hash'])
        self.assertEqual(result['status'],'discarded')
        item=read_document(self.origin,'work-items.yaml')['work_items'][0]
        self.assertEqual(item['status'],'failed')
        self.assertTrue((self.origin/item['integration']['history']).is_file())
        self.assertEqual(ws.mode(self.origin,'direct')['mode'],'direct')

    def test_workspace_updates_blocked_and_custom_runtime_stays_external(self):
        self.assertEqual(ws.update_blockers(self.origin),[self.id])
        self.assertTrue(ws.update_blockers(self.root))
        with self.assertRaises(ValueError):ws.mode(self.origin,'isolated',runtime_root=self.origin/'nested')

    def test_unrelated_new_work_item_during_integration_is_preserved(self):
        completion=self.prepare()
        result=ws.integrate(self.origin,self.id)
        original_publish=ws.publish
        from unittest.mock import patch
        from sdd_core.work_items import update
        other='01951d7f-b507-7200-8000-000000000098'
        def publish_after_new_work(root,identifier,expected,**kwargs):
            update(root,other,'pending',[fixture.A])
            return original_publish(root,identifier,expected,**kwargs)
        with patch('sdd_core.workspaces.publish',side_effect=publish_after_new_work):
            result=ws.integrate(self.origin,self.id,{'preview':content_hash(result['preview']),
                'findings':completion['findings'],'completion':completion})
        self.assertEqual(result['status'],'integrated')
        records=read_document(self.origin,'work-items.yaml')['work_items']
        self.assertEqual({item['id']:item['status'] for item in records},{self.id:'completed',other:'pending'})

    def test_discovery_work_item_stays_pending_without_premature_feature_uuid(self):
        other='01951d7f-b507-7200-8000-000000000097'
        ws.start_discovery(self.origin,other)
        row=read_document(self.origin,'work-items.yaml')['work_items'][-1]
        self.assertEqual(row['declared_features'],[])
        self.assertEqual(row['status'],'pending')
        self.assertTrue(row['discovery_pending'])

    def test_unknown_external_resource_isolation_is_blocked(self):
        self.enter()
        data=ws.registry(self.origin);data['items'][self.id]['execution']['external_resources']='unknown'
        ws.save(ws.runtime_path(self.origin)/'workspaces.json',data)
        with self.assertRaises(ValueError):
            with ws.execution(self.root,['python','-c','pass']):pass

    def test_runtime_temp_env_and_git_ceiling_do_not_mutate_parent_environment(self):
        import os
        self.enter();original=dict(os.environ)
        with ws.execution(self.root,['python','-c','pass']) as env:
            self.assertEqual(env['SPECTHREAD_WORK_ITEM'],self.id)
            self.assertNotEqual(env.get('TMPDIR'),original.get('TMPDIR'))
            self.assertEqual(env['GIT_CEILING_DIRECTORIES'],str(self.root.parent))
        self.assertEqual(dict(os.environ),original)

    def test_terminated_gate_owner_cleans_only_its_owned_child(self):
        import multiprocessing as mp
        import time
        import subprocess
        import sys
        import psutil
        import test_concurrency
        self.prepare()
        command=[sys.executable,'-c',"from pathlib import Path; import os,time; Path('owned.pid').write_text(str(os.getpid())); time.sleep(60)"]
        self.assertEqual(self.f.gate_set(self.id,[self.f.command_gate(command=command)],confirm=True)[0],0)
        ctx=mp.get_context('spawn');output=ctx.Queue()
        process=ctx.Process(target=test_concurrency.execute,args=(str(self.root),self.id,output))
        outsider=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
        def cleanup_outsider():
            if outsider.poll() is None:outsider.terminate()
            outsider.wait(timeout=5)
        self.addCleanup(cleanup_outsider)
        process.start();self.addCleanup(lambda:process.is_alive() and process.terminate())
        deadline=time.monotonic()+10
        while not(self.root/'owned.pid').exists():
            self.assertLess(time.monotonic(),deadline);time.sleep(.02)
        child=psutil.Process(int((self.root/'owned.pid').read_text()))
        process.terminate();process.join(10)
        deadline=time.monotonic()+10
        while child.is_running():
            self.assertLess(time.monotonic(),deadline);time.sleep(.05)
        self.assertIsNone(outsider.poll())
        outsider.terminate();outsider.wait(5)

    def test_explicit_resolution_is_bound_to_source_and_workspace_and_invalidates_on_change(self):
        import hashlib
        self.enter()
        (self.root/'app.py').write_text('value = 2\n')
        (self.origin/'app.py').write_text('value = 3\n')
        preview=ws.candidate(self.origin,self.id)
        self.assertTrue(preview['conflicts'])
        candidate=Path(ws.registry(self.origin)['items'][self.id]['candidate'])
        combined='value = 5  # explicit reviewed combined intent\n'
        (candidate/'app.py').write_text(combined)
        plan={'preview':content_hash(preview),'resolutions':{'app.py':{'action':'write','hash':hashlib.sha256(combined.encode()).hexdigest()}}}
        resolved=ws.candidate(self.origin,self.id,plan)
        self.assertFalse(resolved['conflicts'])
        self.assertEqual((candidate/'app.py').read_text(),combined)
        (self.origin/'app.py').write_text('value = 4\n')
        stale=ws.candidate(self.origin,self.id)
        self.assertTrue(stale['conflicts'])
        self.assertEqual((self.origin/'app.py').read_text(),'value = 4\n')


    def test_process_death_at_publication_and_completion_points_recovers(self):
        import multiprocessing as mp
        completion=self.prepare()
        (self.root/'new-file.txt').write_text('new content')
        preview=ws.integrate(self.origin,self.id)['preview']
        # First write, middle write and final write exercise completed together
        # with app/evidence data under the same recoverable journal.
        for point in (0,1,-1):
            with self.subTest(point=point):
                preview=ws.integrate(self.origin,self.id)['preview']
                plan={'preview':content_hash(preview),'findings':completion['findings'],'completion':completion}
                p=mp.get_context('spawn').Process(target=crash_publication,args=(str(self.origin),self.id,plan,point))
                p.start();p.join(15)
                self.assertEqual(p.exitcode,73)
                self.assertEqual(ws.recover(self.origin)['status'],'recovered')
                ws.prune_dead_workers(self.origin)
                record=read_document(self.origin,'work-items.yaml')['work_items'][0]
                self.assertEqual(record['status'],'pending')
                self.assertFalse((self.origin/'new-file.txt').exists())
                self.assertTrue(self.root.exists())
        preview=ws.integrate(self.origin,self.id)['preview']
        result=ws.integrate(self.origin,self.id,{'preview':content_hash(preview),'findings':completion['findings'],'completion':completion})
        self.assertEqual(result['status'],'integrated')
        self.assertTrue((self.origin/'new-file.txt').is_file())

    def test_claude_same_session_adapter_and_changed_target_guard(self):
        from sdd_core.workspaces import load,save
        marker=self.origin/'.specify/spec-thread.json'
        settings=load(marker);settings['agent']='claude';save(marker,settings)
        (self.root/'adapter.txt').write_text('Core adapter fixture, not a real Claude execution')
        checks={key:True for key in ('same_session','absolute_edit_target','command_cwd','sandbox_access','origin_write_guard','hook_origin_link')}
        plan={'agent':'claude','session':'claude-existing','checks':checks,'evidence':['adapter.txt'],
              'execution':{'external_resources':'none','ports':'dynamic'}}
        ws.enter(self.origin,self.id,plan)
        from unittest.mock import patch
        with patch.dict(__import__('os').environ,{'SPECTHREAD_AGENT_SESSION':'different'}):
            with self.assertRaisesRegex(ValueError,'다른 Agent Session'):ws.guard(self.root,'profile',self.id)
        with patch.dict(__import__('os').environ,{'SPECTHREAD_AGENT_SESSION':'claude-existing'}):
            ws.guard(self.root,'profile',self.id)
            ws.candidate(self.origin,self.id)
            with self.assertRaisesRegex(ValueError,'대상'):ws.guard(self.root,'profile',self.id)
            candidate=Path(ws.registry(self.origin)['items'][self.id]['candidate'])
            plan['scope']='candidate';ws.enter(self.origin,self.id,plan)
            ws.guard(candidate,'profile',self.id)
            with self.assertRaisesRegex(ValueError,'completed'):ws.guard(candidate,'complete',self.id)

    def test_candidate_repairs_survive_preview_and_source_rebase(self):
        self.enter();ws.candidate(self.origin,self.id)
        candidate=Path(ws.registry(self.origin)['items'][self.id]['candidate'])
        (candidate/'repair.txt').write_text('important indirect fix')
        ws.candidate(self.origin,self.id)
        self.assertEqual((candidate/'repair.txt').read_text(),'important indirect fix')
        (self.origin/'source-change.txt').write_text('current source moved')
        preview=ws.candidate(self.origin,self.id)
        self.assertTrue(any(row['path']=='repair.txt' for row in preview['conflicts']))
        row=ws.registry(self.origin)['items'][self.id]
        self.assertTrue(any((Path(path['path'])/'repair.txt').read_text()=='important indirect fix' for path in row['retained_candidates']))

    def test_publication_create_delete_directories_modes_and_exact_recovery(self):
        import stat
        self.enter();old=self.origin/'old.txt';old.write_text('old')
        # New source additions after snapshot must survive the Work changes.
        (self.root/'new-dir').mkdir();(self.root/'new-dir/new.txt').write_text('new')
        (self.root/'app.py').chmod(0o755)
        preview=ws.candidate(self.origin,self.id)
        before=ws.tree(self.origin);dirs=ws.directory_tree(self.origin)
        def fault(index):
            if index==2:raise RuntimeError('real write boundary')
        with self.assertRaises(RuntimeError):ws.publish(self.origin,self.id,preview['source'],fault=fault)
        ws.recover(self.origin)
        self.assertEqual(ws.tree(self.origin),before);self.assertEqual(ws.directory_tree(self.origin),dirs)
        ws.publish(self.origin,self.id,preview['source'])
        self.assertEqual((self.origin/'new-dir/new.txt').read_text(),'new')
        self.assertEqual(stat.S_IMODE((self.origin/'app.py').stat().st_mode),stat.S_IMODE((self.root/'app.py').stat().st_mode))
        self.assertTrue(old.exists())

    def test_two_workspaces_integrate_sequentially_and_preserve_both_records(self):
        first_completion=self.prepare();(self.root/'first-feature.txt').write_text('first intent')
        first_id,first_root=self.id,self.root
        self.f.root=self.origin
        code,out,error=self.f.cli('start',fixture.A);self.assertEqual(code,0,error)
        other=json.loads(out);self.id=other['work_item'];self.root=Path(other['workspace'])
        second_completion=self.prepare();(self.root/'second-feature.txt').write_text('second intent')
        second_id=self.id
        for identifier,completion in ((first_id,first_completion),(second_id,second_completion)):
            preview=ws.integrate(self.origin,identifier)['preview']
            self.assertFalse(preview['conflicts'])
            result=ws.integrate(self.origin,identifier,{'preview':content_hash(preview),'findings':completion['findings'],'completion':completion})
            self.assertEqual(result['status'],'integrated')
        self.assertEqual((self.origin/'first-feature.txt').read_text(),'first intent')
        self.assertEqual((self.origin/'second-feature.txt').read_text(),'second intent')
        items=read_document(self.origin,'work-items.yaml')['work_items']
        self.assertEqual({row['id']:row['status'] for row in items},{first_id:'completed',second_id:'completed'})
        self.assertTrue(all(row.get('gate_results') for row in items))

    def test_snapshot_waits_for_publish_but_not_for_long_integration(self):
        import multiprocessing as mp
        import threading,time
        from sdd_core.work_items import update
        from sdd_core.cli import uuid7
        context=mp.get_context('spawn')
        for lock_name in ('integration','publish'):
            identifier=str(uuid7());update(self.origin,identifier,'pending',[fixture.A])
            ready=context.Event();owner=context.Process(target=own_lock,args=(str(self.origin),lock_name,ready))
            owner.start();self.assertTrue(ready.wait(5))
            results=[];errors=[]
            def create():
                try:results.append(ws.create(self.origin,identifier))
                except Exception as error:errors.append(error)
            thread=threading.Thread(target=create);thread.start()
            try:
                if lock_name=='integration':
                    thread.join(3);self.assertEqual(len(results),1,errors)
                else:
                    time.sleep(.15);self.assertFalse(results);self.assertTrue(thread.is_alive())
            finally:owner.terminate();owner.join(5);thread.join(5)
            self.assertFalse(errors);self.assertEqual(len(results),1)

    def test_dead_waiter_is_removed_but_live_kernel_owner_is_preserved(self):
        import multiprocessing as mp
        context=mp.get_context('spawn');ready=context.Event()
        owner=context.Process(target=own_lock,args=(str(self.origin),'worker-'+self.id,ready))
        owner.start();self.assertTrue(ready.wait(5))
        try:
            data=ws.registry(self.origin);data['queue']=[{'id':self.id,'queued_at':0,'worker':'actual-kernel-owner'}]
            data['items'][self.id]['state']='waiting';ws.save(ws.runtime_path(self.origin)/'workspaces.json',data)
            ws.prune_dead_workers(self.origin)
            self.assertEqual(len(ws.registry(self.origin)['queue']),1)
        finally:owner.terminate();owner.join(5)
        ws.prune_dead_workers(self.origin)
        data=ws.registry(self.origin)
        self.assertEqual(data['queue'],[]);self.assertEqual(data['items'][self.id]['state'],'blocked')

    def test_resolution_limit_requires_explicit_current_resume_decision(self):
        import hashlib
        completion=self.prepare();ws.mode(self.origin,limits={'resolution_attempts':1})
        (self.origin/'conflict.txt').write_text('source intent')
        (self.root/'conflict.txt').write_text('work intent')
        preview=ws.integrate(self.origin,self.id)['preview']
        candidate=Path(ws.registry(self.origin)['items'][self.id]['candidate'])
        content=b'both intents explicitly resolved';(candidate/'conflict.txt').write_bytes(content)
        resolved=ws.candidate(self.origin,self.id,{'preview':content_hash(preview),'resolutions':{'conflict.txt':{'action':'write','hash':hashlib.sha256(content).hexdigest()}}})
        plan={'preview':content_hash(resolved),'findings':completion['findings'],'completion':completion}
        blocked=ws.integrate(self.origin,self.id,plan)
        self.assertEqual(blocked['status'],'blocked');self.assertIn('resume_hash',blocked)
        plan['resume_confirm']=blocked['resume_hash']
        result=ws.integrate(self.origin,self.id,plan)
        self.assertEqual(result['status'],'integrated')
