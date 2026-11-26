"""Core contract comparison, NOT native Skill/LLM policy or productivity evidence.

Run against the preserved source using PYTHONPATH, then current source. Both run
identical fixtures; no artificial pre-change server/report overhead is assumed.
Uses real defect assertions and an owned ephemeral loopback server when needed.
"""
import json
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_verification_profiles import VerificationProfilesTest, A
from test_lifecycle_gates import B
from sdd_core import __version__
from sdd_core.records import read_document, write_document

CASES = ('bug-large-feature', 'local-extension', 'api-contract', 'multiple-features', 'live-network')

def sample(case, agent):
    f = VerificationProfilesTest('test_lightweight_minimum_and_missing_procedures_block_completion')
    f.setUp()
    try:
        # Install a separate native bundle of the selected kind, not an agent run.
        from sdd_core.version_sync import install_skills
        if agent == 'claude':
            import shutil
            shutil.rmtree(f.root / '.agents')
            (f.root / '.specify/spec-thread.json').unlink()
            baseline=f.root/'.specify/baseline';saved=f.root/'saved-baseline';baseline.rename(saved)
            install_skills(f.root, agent)
            saved.rename(baseline)
        f.write('specs/a/spec.md', '# Existing approved requirements\n' + ''.join(f'R{i}: preserve unrelated behavior {i}.\n' for i in range(600)))
        f.write('user-notes.txt', 'Existing user edit must survive\n')
        before = {name:(f.root/name).read_bytes() for name in ('specs/a/spec.md','specs/a/plan.md','specs/b/spec.md','user-notes.txt')}
        identifier = f.pending()
        p = f.classification()
        if case in ('local-extension', 'api-contract', 'multiple-features'):
            p['risks']['contract_changed'] = True
        if case == 'api-contract':
            p['risks']['breaking_api'] = True
            p['considerations'] = {n:{'required':False,'reason':'Isolated contract assertion covers this bounded fixture; no global mandatory official review'} for n in ('checklist','analyze','converge')}
        if case == 'multiple-features':
            report = f.analysis['features'][A]
            f.analysis['features'][B] = report
            f.analyze()
            path=f.plan('expand.json',{'features':[B],'reason':'Observed direct consumer needs the new contract'})
            code,out,err=f.cli('scope-expand',identifier,path);assert code==0,err
            assert f.cli('scope-expand',identifier,path,'--confirm',json.loads(out)['approval_hash'])[0]==0
        assert f.classify(identifier,p,approve=case=='api-contract')[0]==0
        if case=='multiple-features':f.write('specs/b/tasks.md','- [x] T001 Verify affected consumer\n')
        f.procedures(identifier)
        if p['risks']['contract_changed']:
            f.write('specs/a/spec.md', before['specs/a/spec.md'].decode()+'\nApproved extension: return value 2.\n')
            f.analyze()
            assert f.cli('procedure',identifier,'specify',f.plan('spec-step.json',{'status':'done','conclusion':'Fixture approved extension recorded','evidence':['specs/a/spec.md']}))[0]==0
        # A real test discovers a seeded defect, then succeeds after repair.
        f.write('app.py','value = 0\n')
        if case == 'live-network':
            test = '''from http.server import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
from urllib.request import urlopen
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()))
import app
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(str(app.value).encode())
 def log_message(self,*args):pass
server=HTTPServer(('127.0.0.1',0),Handler)
thread=Thread(target=server.serve_forever);thread.start()
try:
 assert urlopen('http://127.0.0.1:%d'%server.server_port,timeout=3).read()==b'2'
 Path('test-result.txt').write_text('Actual HTTP body and connection PASS')
finally:
 server.shutdown();server.server_close();thread.join()
'''
        else:
            test = "from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path.cwd()))\nimport app\nassert app.value==2, 'seeded regression'\nPath('test-result.txt').write_text('Actual behavior assertion PASS')\n"
        if case=='api-contract':
            test="from pathlib import Path\nimport sys;sys.path.insert(0,str(Path.cwd()))\nimport app\nassert app.response('ok')=={'count':2}\ntry:app.response(None)\nexcept ValueError:pass\nelse:raise AssertionError('invalid request accepted')\nPath('test-result.txt').write_text('Real function API response and error PASS')\n"
            f.write('app.py',"def response(value):\n if value is None:raise ValueError('invalid request')\n return {'count':0}\n")
        if case=='multiple-features':
            f.write('consumer.py','import app\ndef consume():return app.value + 1\n')
            test="from pathlib import Path\nimport sys;sys.path.insert(0,str(Path.cwd()))\nimport consumer\nassert consumer.consume()==3\nPath('test-result.txt').write_text('Actual direct consumer PASS')\n"
        f.write('tests/check_behavior.py',test)
        gate=f.command_gate(command=[sys.executable,'tests/check_behavior.py'])
        gate['paths']=['app.py','tests/check_behavior.py']
        if case=='multiple-features':gate['paths'].append('consumer.py')
        if case=='multiple-features':gate['targets']=[A,B]
        assert f.gate_set(identifier,[gate])[0]==0
        assert f.cli('transition',identifier,'in_progress')[0]==0
        started=time.perf_counter();bad=f.cli('gate-run',identifier,'project-tests')
        assert bad[0]==2,bad
        assert 'AssertionError' in json.loads(bad[1])['execution']['stderr'],bad
        edit=time.perf_counter();f.write('app.py',"def response(value):\n if value is None:raise ValueError('invalid request')\n return {'count':2}\n" if case=='api-contract' else 'value = 2\n');implementation=time.perf_counter()-edit
        good=f.cli('gate-run',identifier,'project-tests');assert good[0]==0,good
        reused=f.cli('gate-run',identifier,'project-tests');assert json.loads(reused[1])['action']=='reuse'
        verified=time.perf_counter()-started
        # Defect repair changes same-size Python quickly: use source execution in tests,
        # disable bytecode caching so the repeat cannot accidentally use stale imports.
        complete={'actual_features':[A,B] if case=='multiple-features' else [A],
                  'findings':[{'assessment':'SAFE','evidence':'Seeded defect detected, repaired assertion PASS, bounded fixture checked'}],
                  'evidence':[{'ref':'test-result.txt'}]}
        result=f.cli('complete',identifier,f.plan('finish.json',complete));assert result[0]==0,result
        preserved={name:(f.root/name).read_bytes()==data for name,data in before.items()}
        assert all(v for n,v in preserved.items() if n!='specs/a/spec.md'),preserved
        assert preserved['specs/a/spec.md']==(not p['risks']['contract_changed'])
        return {'scenario':case,'agent_bundle':agent,'core':__version__,'implementation_seconds':implementation,
                'verification_seconds':verified,'actual_tests':2,'live_server_starts':2 if case=='live-network' else 0,
                'seeded_defect_detected':True,'completed':True,'third_gate_request':'reuse','preserved':preserved,
                'semantic_documents_modified':1 if p['risks']['contract_changed'] else 0,'extra_reports':0,
                'native_agent':False,'llm_tokens':None,'document_analysis_seconds':None,'official_skill_calls':None}
    finally:
        f.doCleanups()

if __name__=='__main__':
    # Prevent stale app.py bytecode during rapid subprocess fixture repair.
    import os
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    rows=[sample(case,agent) for repeat in range(2) for agent in ('codex','claude') for case in CASES]
    print(json.dumps({'core':__version__,'samples':rows,'median_verification_seconds':median(x['verification_seconds'] for x in rows),
                     'limits':['Identical scripted Core fixtures, not native model or semantic Skill execution',
                               'No full development/document reads/tokens/human dialogs measured',
                               'No fabricated before-change redundant server or report work']},indent=2))
