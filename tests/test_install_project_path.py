"""Remembered target is a confirmed preference, never an unattended destination."""
import io
import json
import os
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ProjectPathTest(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.source=self.base/'distribution';self.source.mkdir()
        self.app=self.base/'앱 project';self.app.mkdir();(self.app/'.specify').mkdir()
        (self.app/'.specify/spec-thread.json').write_text('{"agent":"codex"}')
        self.other=self.base/'another app';self.other.mkdir()
        self.cache=self.base/'cache'
        self.module=runpy.run_path(str(Path(__file__).resolve().parents[1]/'specthread'))
        self.select=self.module['select_project'];self.remember=self.module['remember_project']

    def select_from_distribution(self,answers,**kwargs):
        prompts=[];iterator=iter(answers)
        def ask(prompt):prompts.append(prompt);return next(iterator)
        with patch('pathlib.Path.cwd',return_value=self.source):
            result=self.select('update',kwargs.get('explicit'),self.source,self.cache,kwargs.get('interactive',True),ask=ask)
        return result,prompts

    def test_confirm_last_app_from_new_distribution(self):
        self.remember(self.cache,self.app)
        result,prompts=self.select_from_distribution(['y'])
        self.assertEqual(result,self.app);self.assertEqual(len(prompts),1);self.assertIn(str(self.app),prompts[0])
        self.assertEqual(self.select_from_distribution([''])[0],self.app)

    def test_reject_last_app_and_enter_quoted_path(self):
        self.remember(self.cache,self.app)
        result,prompts=self.select_from_distribution(['n','"'+str(self.other)+'"'])
        self.assertEqual(result,self.other);self.assertEqual(len(prompts),2)
        self.assertEqual(json.loads((self.cache/'last-project.json').read_text())['project'],str(self.app))

    def test_missing_deleted_and_corrupt_preferences_ask_for_path(self):
        self.cache.mkdir()
        for content in (None,'invalid json','[]',json.dumps({'schema_version':1,'project':str(self.base/'deleted')})):
            with self.subTest(content=content):
                path=self.cache/'last-project.json'
                if content is None:path.unlink(missing_ok=True)
                else:path.write_text(content)
                result,prompts=self.select_from_distribution([str(self.app)])
                self.assertEqual(result,self.app);self.assertEqual(len(prompts),1)
                self.assertNotIn('맞나요',prompts[0])

    def test_explicit_and_current_installed_project_take_precedence(self):
        self.remember(self.cache,self.app)
        result,prompts=self.select_from_distribution([],explicit=self.other)
        self.assertEqual(result,self.other);self.assertFalse(prompts)
        (self.other/'.specify').mkdir();(self.other/'.specify/spec-thread.json').write_text('{}')
        with patch('pathlib.Path.cwd',return_value=self.other):
            prompts=[]
            result=self.select('update',None,self.source,self.cache,True,ask=lambda prompt:prompts.append(prompt) or '네')
        self.assertEqual(result,self.other);self.assertIn(str(self.other),prompts[0])

    def test_noninteractive_never_selects_remembered_project(self):
        self.remember(self.cache,self.app)
        with patch('pathlib.Path.cwd',return_value=self.other):
            result=self.select('update',None,self.source,self.cache,False,ask=lambda _:self.fail('unexpected prompt'))
        self.assertEqual(result,self.other)

    def test_failed_bootstrap_does_not_replace_saved_target(self):
        self.remember(self.cache,self.app)
        target=self.other;(target/'.specify').mkdir();(target/'.specify/spec-thread.json').write_text('{"agent":"codex"}')
        main=self.module['main'];env={'SPEC_THREAD_CACHE':str(self.cache)}
        for status in (1,0):
            with patch.dict(os.environ,env),patch('sys.argv',['specthread','update','--project',str(target),'--yes']),patch('sys.stdin',io.StringIO('')),patch.dict(main.__globals__,{'install_packages':lambda folder,*a,**k:folder.mkdir(parents=True,exist_ok=True)}),patch('subprocess.run',return_value=SimpleNamespace(returncode=status)):
                self.assertEqual(main(),status)
            expected=self.app if status else target
            self.assertEqual(json.loads((self.cache/'last-project.json').read_text())['project'],str(expected))
