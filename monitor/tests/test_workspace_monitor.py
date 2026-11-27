"""Registered external paths only, with original Git scope unchanged."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
import test_workspaces as core_fixture
from specthread_monitor.server import MonitorServer
from specthread_monitor import session
from specthread_monitor.events import collect
from sdd_core import workspaces as ws


class WorkspaceMonitorTest(unittest.TestCase):
    def setUp(self):
        self.f=core_fixture.WorkspaceTest('test_snapshot_is_content_not_only_manifest_and_files_are_independent')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.origin=self.f.origin;self.workspace=self.f.root

    def test_registered_workspace_scope_and_arbitrary_external_path_denied(self):
        with MonitorServer(self.origin,[],0) as server:
            listing=server.workspace_list()
            self.assertEqual([row['id'] for row in listing],[self.f.id])
            view=server.workspace_snapshot(self.f.id)
            self.assertFalse(view['workspace_context']['published'])
            self.assertIsNone(view['git'])
            with self.assertRaises(ValueError):server.workspace_root('../../outside')
            with self.assertRaises(ValueError):server.workspace_root(self.f.id,'/etc')

    def test_workspace_hook_is_recorded_once_under_original_project_and_same_session(self):
        raw={'cwd':str(self.workspace),'session_id':'same-existing-session','hook_event_name':'UserPromptSubmit'}
        stream=io.TextIOWrapper(io.BytesIO(json.dumps(raw).encode()))
        records=[]
        with patch('sys.stdin',stream),patch('specthread_monitor.session.record',side_effect=lambda *args:records.append(args)),patch('specthread_monitor.session.reader_response',return_value=None):
            session.record_event(self.origin,'claude')
        self.assertEqual(len(records),1)
        root,agent,event=records[0]
        self.assertEqual(root,self.origin.resolve())
        self.assertEqual(event['workspace'],self.f.id)
        self.assertEqual(event['session_id'],'same-existing-session')
        event.update(agent='claude',observed_at=__import__('time').time())
        activity=collect(self.origin.resolve(),[],[('hook-event',event)])
        self.assertEqual(activity['sessions'][0]['workspace'],self.f.id)

    def test_origin_event_clears_workspace_context_without_losing_history(self):
        import time
        rows=[('one',{'agent':'claude','session_id':'same-session','hook_event_name':'UserPromptSubmit','cwd':str(self.origin),
                     'workspace':self.f.id,'observed_at':time.time()}),
              ('two',{'agent':'claude','session_id':'same-session','hook_event_name':'UserPromptSubmit','cwd':str(self.origin),
                     'observed_at':time.time()})]
        result=collect(self.origin.resolve(),[],rows)
        self.assertNotIn('workspace',result['sessions'][0])
        self.assertEqual(result['events'][0]['workspace'],self.f.id)
