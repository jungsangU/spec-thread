"""Reproduce unrelated-work invalidation using real processes; no native agent run.

Select preserved/current Core with absolute PYTHONPATH. Measurements cover Core
contract execution only, never model productivity or token counts.
"""
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
from statistics import median

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import test_verification_profiles as fixtures
from sdd_core import __version__
from sdd_core.gates import execute_gate
from sdd_core.records import read_document,write_document


def worker(root,id,out):
    started=time.perf_counter()
    try:
        result=execute_gate(Path(root),id,'project-tests')
        out.put({'id':id,'status':result['status'],'seconds':time.perf_counter()-started})
    except Exception as error:
        out.put({'id':id,'status':'ERROR','error':str(error),'seconds':time.perf_counter()-started})


def sample(parallel):
    f=fixtures.VerificationProfilesTest('test_lightweight_minimum_and_missing_procedures_block_completion');f.setUp()
    try:
        ids=[]
        for index in range(2 if parallel else 1):
            id=f.pending();f.classify(id);ids.append(id)
            code="from pathlib import Path; import time; Path('ready-%d').touch();\nwhile not Path('release').exists():time.sleep(.01)\nassert Path('app.py').read_text().strip()=='value = 1'; Path('result-%d.txt').write_text('Actual assertion PASS')"%(index,index) if parallel else "from pathlib import Path; assert Path('app.py').read_text().strip()=='value = 1'; Path('result-0.txt').write_text('Actual assertion PASS')"
            gate=f.command_gate(command=[sys.executable,'-c',code]);gate['evidence']=['result-%d.txt'%index]
            assert f.gate_set(id,[gate])[0]==0
        started=time.perf_counter()
        if parallel:
            ctx=mp.get_context('spawn');out=ctx.Queue()
            processes=[ctx.Process(target=worker,args=(str(f.root),id,out)) for id in ids]
            for p in processes:p.start()
            try:
                deadline=time.monotonic()+10
                while not all((f.root/('ready-%d'%i)).exists() for i in range(2)):
                    if time.monotonic()>deadline:raise RuntimeError('worker timeout')
                    time.sleep(.01)
                doc=read_document(f.root,'work-items.yaml')
                doc['work_items'].append({'id':'01951d7f-b507-7200-8000-000000000099','status':'failed','declared_features':[],'actual_features':[]})
                write_document(f.root,'work-items.yaml',doc)
                (f.root/'release').touch()
                for p in processes:p.join(10)
                results=[out.get(timeout=2) for p in processes]
            finally:
                for p in processes:
                    if p.is_alive():p.terminate();p.join()
        else:
            result=execute_gate(f.root,ids[0],'project-tests');results=[{'status':result['status']}]
        return {'parallel':parallel,'seconds':time.perf_counter()-started,'results':results,
                'false_invalidations':sum(row['status']=='ERROR' for row in results),'native_agent':False}
    finally:f.doCleanups()


if __name__=='__main__':
    rows=[sample(parallel) for parallel in (False,True) for _ in range(3)]
    print(json.dumps({'core':__version__,'samples':rows,
                     'single_median_seconds':median(row['seconds'] for row in rows if not row['parallel']),
                     'parallel_median_seconds':median(row['seconds'] for row in rows if row['parallel']),
                     'false_invalidations':sum(row['false_invalidations'] for row in rows)},indent=2))
