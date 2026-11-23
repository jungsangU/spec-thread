"""Execute the current Markdown JSON examples against an isolated Core fixture.

Run with Python 3.11+ and the product dependency PyYAML. This is not an official
Spec Kit/agent end-to-end test. Only temporary target-project files are mutated.
"""
import os,sys,json,re,subprocess,tempfile,hashlib
from pathlib import Path
import yaml
repo=Path(__file__).resolve().parents[1];docs=repo/'docs/design'
fixture=tempfile.TemporaryDirectory(prefix='specthread-document-contract-')
work=Path(fixture.name)
env={**os.environ,'PYTHONPATH':str(repo/'src')}
checks=[]
def code(name):return [json.loads(s) for s in re.findall(r'```json\n(.*?)\n```',(docs/name).read_text(),re.S)]
def write(name,s):
 p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def cli(*args,expect=0):
 r=subprocess.run([sys.executable,'-m','sdd_core.cli','--root',str(work),*args],env=env,text=True,capture_output=True)
 assert r.returncode==expect,(args,expect,r.returncode,r.stdout,r.stderr)
 return r.stdout.strip(),r.stderr

def plan(name,obj):write(name,json.dumps(obj,ensure_ascii=False));return str(work/name)
def document(name):return yaml.safe_load((work/'.specify/baseline'/name).read_text())
def record(label):checks.append(label)
# Isolated Core contract fixture; .specify is a stub, not evidence of official Spec Kit integration.
(work/'.specify').mkdir();cli('install-skills','codex');cli('scaffold');cli('validate')
write('specs/example/spec.md','# Example\nPurpose: value is one.\n')
write('specs/example/plan.md','# Plan\nUse app.py and existing unittest verification.\n')
write('basis.md','Scope, requirement and independent unanalysed boundary reviewed in this isolated fixture.\n')
write('verification-rules.md','Use the existing unittest suite and preserve test-results.txt.\n')
write('app.py','value = 1\n')
write('tests/test_app.py',"import unittest\nfrom pathlib import Path\nimport app\nclass AppTest(unittest.TestCase):\n def test_value(self):\n  self.assertEqual(app.value,1)\n  Path('test-results.txt').write_text('unittest: value is one; PASS\\n')\n")
discovery,registration,analysis=code('03-analysis-standard.md')
p=plan('discovery.json',discovery)
assert json.loads(cli('discovery-gate',p)[0])['verdict']=='READY'
conditional=json.loads(json.dumps(discovery));conditional['checks']['scope']={'status':'condition','critical':False,'evidence':'nonessential fixture question','next_step':'review later'}
assert json.loads(cli('discovery-gate',plan('conditional.json',conditional))[0])['verdict']=='CONDITIONAL'
conditional['checks']['scope'].pop('critical')
assert json.loads(cli('discovery-gate',plan('blocked.json',conditional))[0])['verdict']=='BLOCKED'
record('Discovery READY/CONDITIONAL/BLOCKED and critical-default rule')
registration['discovery']=discovery
feature=cli('feature-register',plan('register.json',registration))[0]
assert document('features.yaml')['features'][0]['id']==feature
cli('start',feature,expect=1);record('not_started blocks start')
analysis['features'][feature]=analysis['features'].pop('<FEATURE_UUID>');analysis['features'][feature]['discovery']=discovery
cli('analysis-record',plan('analysis.json',analysis));cli('develop-check',feature);record('partial plus READY recorded from documented JSON permits development')
wi=cli('start',feature)[0]
cli('transition',wi,'in_progress',expect=1)
gateplan=code('06-verification.md')[0]
gateplan['gates'][0]['targets']=[feature];gateplan['gates'][0]['command'][0]=sys.executable
path=plan('gates.json',gateplan)
def define(id):
 preview=json.loads(cli('gates',id,path)[0]);cli('gates',id,path,'--confirm',preview['approval_hash'])
define(wi);cli('transition',wi,'in_progress');cli('stage-check',wi,'complete',expect=1)
record('Gate set required before entry; NOT_RUN blocks completion')
run=json.loads(cli('gate-run',wi,'project-tests')[0]);assert run['status']=='PASS';record('documented Gate argv executes real unittest and evidence')
# Avoid cached module timing when mutating test input: run invalid Python then restore.
write('app.py','raise RuntimeError("fixture repairable failure")\n')
cli('stage-check',wi,'complete',expect=1)
run=json.loads(cli('gate-run',wi,'project-tests',expect=2)[0]);assert run['status']=='FAIL'
assert document('work-items.yaml')['work_items'][0]['status']=='in_progress';record('changed input invalidates PASS; test failure preserves in_progress')
write('app.py','value = 1\n');assert json.loads(cli('gate-run',wi,'project-tests')[0])['status']=='PASS'
cli('stage-check',wi,'complete')
completion=code('SpecThread-설계와-실행-가이드.md')[0];completion['actual_features']=[feature];completion['evidence']=[{'ref':'test-results.txt'}]
cli('complete',wi,plan('complete.json',completion));assert document('work-items.yaml')['work_items'][0]['status']=='completed'
cli('transition',wi,'in_progress',expect=1);record('documented completion plan records completed; reopening blocked')
# Independently calculate persisted hashes using the formulas in the design, without importing Core internals.
def ch(v):return 'sha256:'+hashlib.sha256(json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()).hexdigest()
item=document('work-items.yaml')['work_items'][0];rev=item['gate_revisions'][-1];run=item['gate_results']['project-tests'][-1]
assert rev['hash']==ch({k:v for k,v in rev.items() if k!='hash'})
assert run['definition_hash']==ch({**rev['gates'][0],'revision':rev['hash']})
assert item['validation']['fingerprint']==ch(run['inputs']);record('revision, definition and completion fingerprint reproduced from documented formulas')
# Exercise the new reconciliation JSON directly from its topic document.
sync=code('reconciliation.md')[0]
sync['base']={'kind':'files','refs':['basis.md']}
sync['features']=[feature]
sync['basis']=['basis.md']
sync['changes'][0]['path']='specs/example/spec.md'
sync['verification']=gateplan
sp=plan('sync.json',sync)
approval=json.loads(cli('reconcile',sp)[0])['approval_hash']
sync_id=json.loads(cli('reconcile',sp,'--confirm',approval)[0])['work_item']
record('documented reconciliation plan binds approval and creates Work Item')
preview=json.loads(cli('gate-refresh',sync_id)[0])
assert json.loads(cli('gate-refresh',sync_id,'--confirm',preview['approval_hash'])[0])['status']=='PASS'
cli('complete',sync_id,plan('sync-complete.json',completion))
cli('analysis-record',plan('analysis-after-sync.json',analysis))
record('selective refresh runs required checks and reconciliation completes with preserved history')
failed=cli('start',feature)[0];define(failed);cli('transition',failed,'in_progress');cli('transition',failed,'failed');cli('transition',failed,'in_progress',expect=1)
retry=cli('start',feature,'--related',failed)[0];assert retry!=failed
assert document('work-items.yaml')['work_items'][-1]['related_work_items']==[failed];record('failed terminal; retry new UUID with previous history reference')
retirement=code('feature-lifecycle.md')[0];rp=plan('retire.json',retirement)
cli('feature-retire',feature,rp,expect=1);record('in-flight Work Item prevents retirement')
define(retry);cli('transition',retry,'in_progress');cli('transition',retry,'failed')
history=(work/'.specify/baseline/work-items.yaml').read_bytes()
preview=json.loads(cli('feature-retire',feature,rp)[0]);assert not (work/'docs/sdd/archive'/feature).exists()
cli('feature-retire',feature,rp,'--confirm',preview['approval_hash']);cli('validate')
f=document('features.yaml')['features'][0];assert f['id']==feature and f['status']=='retired' and f['spec_path']=='docs/sdd/archive/'+feature
assert history==(work/'.specify/baseline/work-items.yaml').read_bytes();cli('develop-check',feature,expect=1)
record('archive preview read-only; approval moves files preserving UUID/history; retired development blocked')
result={'fixture':str(work),'status':'passed','checks':checks,'limits':['Core contract fixture only; .specify is a stub, not a real Spec Kit installation','No Codex/Claude official skill delegation or real project end-to-end PoC']}
print(json.dumps(result,ensure_ascii=False,indent=2))
