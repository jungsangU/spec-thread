"""Repeatable Core-only comparison. Select the Core with PYTHONPATH.

Uses real subprocess assertions, six isolated samples, and preconfigured policy.
Does not measure a native agent, model tokens, human dialogs, or full development.
The 0.4.0 baseline can be exported read-only from commit 035ba12.
"""
import contextlib,io,json,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from statistics import median
from sdd_core import __version__
from sdd_core.cli import main
from sdd_core.baseline import scaffold
from sdd_core.version_sync import install_skills
from sdd_core.records import read_document,write_document
from sdd_core.analysis import record_analysis
A='01951d7f-b507-7200-8000-000000000001'
new=tuple(map(int,__version__.split('.'))) >= (0,5,0)
def sample(agent):
 with TemporaryDirectory(prefix='specthread-profile-compare-') as folder:
  root=Path(folder);(root/'.specify').mkdir();install_skills(root,agent);scaffold(root)
  def write(name,text):
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
  def plan(name,value):write(name,json.dumps(value));return str(root/name)
  def cli(*args):
   with contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()) as err:
    code=main(['--root',str(root),*args])
   if code:raise RuntimeError((args,code,out.getvalue(),err.getvalue()))
   return out.getvalue().strip()
  write('specs/ui/spec.md','# UI\nDisplay the approved label; no API/schema change.\n')
  write('specs/ui/plan.md','# Plan\nKeep the label constant and existing behavior test.\n')
  write('specs/ui/tasks.md','- [ ] T001 Update approved label\n')
  write('app.py',"LABEL = 'Before'\n")
  write('verification-rules.md','Existing label regression test covers the approved request.\n')
  write('tests/check_label.py',"from pathlib import Path\nscope={}\nexec(Path('app.py').read_text(),scope)\np=Path('runs.txt');p.write_text(str(int(p.read_text())+1) if p.exists() else '1')\nassert scope['LABEL']=='After'\nPath('test-result.txt').write_text('actual label regression PASS')\n")
  doc=read_document(root,'features.yaml');doc['features']=[{'id':A,'name':'UI label','status':'active','spec_path':'specs/ui','dependencies':[]}];write_document(root,'features.yaml',doc)
  discovery={'mode':'greenfield','candidate':'UI label','checks':{key:{'status':'verified','evidence':'specs/ui/spec.md'} for key in ('scope','boundaries','requirements','spec_quality','workflow')}}
  record_analysis(root,{'status':'complete','unanalysed':[],'paths':['specs/ui/spec.md'],'evidence':['specs/ui/spec.md'],'features':{A:{'discovery':discovery,'dependencies':[{'assessment':'SAFE','evidence':'UI constant has no callers or external contract dependencies in the fixture'}]}}})
  gate={'id':'label-regression','rationale':'Approved label retains the public contract','purpose':'ui.label', 'required':True,'required_for':['complete'],'targets':[A], 'kind':'command','command':[sys.executable,'tests/check_label.py'],'paths':['app.py','tests/check_label.py'],'evidence':['test-result.txt'],'evidence_requirement':'Actual label assertion result'}
  if new:
   from sdd_core.verification import empty_registry,RISKS
   catalog=empty_registry();catalog.update(status='configured',reason='Known existing test method',basis=['verification-rules.md'])
   catalog['project']['gates']=[{**gate,'targets':'$scope','mandatory':True,'profiles':['lightweight','standard','strict']}]
   write_document(root,'verification.yaml',catalog)
  started=time.perf_counter();cli('preflight','develop','--agent',agent,A);id=cli('start',A)
  if new:
   cli('profile',id,plan('profile.json',{'reason':'Local UI copy, existing contract preserved','basis':['verification-rules.md'],'risks':{key:False for key in RISKS},'findings':[{'assessment':'SAFE','evidence':'Source, tests and unchanged contract checked'}]}),'--apply')
   for step,ref in [('plan','specs/ui/plan.md'),('tasks','specs/ui/tasks.md')]:
    cli('procedure',id,step,plan('step.json',{'status':'reused' if step=='plan' else 'done','conclusion':'Actual current artifact checked','evidence':[ref]}))
  gp=plan('gates.json',{'reason':'Use the existing label regression','basis':['verification-rules.md'],'gates':[] if new else [gate]})
  if new:cli('gates',id,gp,'--compose','--apply')
  else:
   preview=json.loads(cli('gates',id,gp));cli('gates',id,gp,'--confirm',preview['approval_hash'])
  cli('transition',id,'in_progress');implementation_start=time.perf_counter()
  write('app.py',"LABEL = 'After'\n");write('specs/ui/tasks.md','- [x] T001 Update approved label\n')
  implementation_seconds=time.perf_counter()-implementation_start
  if new:cli('procedure',id,'implement',plan('step.json',{'status':'done','conclusion':'Actual label implementation changed','evidence':['app.py','specs/ui/tasks.md']}))
  verify_start=time.perf_counter();first=json.loads(cli('gate-run',id,'label-regression'));second=json.loads(cli('gate-run',id,'label-regression'));verification_seconds=time.perf_counter()-verify_start
  cli('complete',id,plan('complete.json',{'actual_features':[A],'findings':[{'assessment':'SAFE','evidence':'Actual label assertion passed; unchanged API/schema'}],'evidence':[{'ref':'test-result.txt'}]}))
  return {'agent':agent,'core':__version__,'core_request_seconds':time.perf_counter()-started,'implementation_seconds':implementation_seconds,'verification_seconds':verification_seconds,'actual_test_runs':int((root/'runs.txt').read_text()),'required_explicit_gate_plan_confirmations':0 if new else 1,'second_result_action':second.get('action','run'),'completed':read_document(root,'work-items.yaml')['work_items'][0]['status']=='completed'}
rows=[sample(agent) for agent in ('codex','claude') for _ in range(3)]
print(json.dumps({'core':__version__,'samples':rows,'median_core_request_seconds':median(row['core_request_seconds'] for row in rows),'median_verification_seconds':median(row['verification_seconds'] for row in rows),'limits':['Core workflow microbenchmark, not a native LLM agent run','Same Python/runtime/request/source/test; new registry configured before timing','No actual model token or human dialog measurement']},ensure_ascii=False,indent=2))
