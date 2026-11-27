"""Per-command child ownership. Not a persistent watcher or test engine."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time


def identity(pid):
    import psutil
    try:
        process=psutil.Process(pid)
        return {'pid':pid,'created':process.create_time()}
    except psutil.NoSuchProcess:return None


def same_process(owner):
    import psutil
    try:
        process=psutil.Process(owner['pid'])
        return process if process.create_time()==owner['created'] and process.status()!=psutil.STATUS_ZOMBIE else None
    except psutil.NoSuchProcess:return None


def owned_cleanup(processes):
    import psutil
    live=[]
    for process in reversed(processes):
        try:
            if process.is_running():process.terminate();live.append(process)
        except psutil.NoSuchProcess:pass
    _,remaining=psutil.wait_procs(live,timeout=2)
    for process in remaining:
        try:
            if process.is_running():process.kill()
        except psutil.NoSuchProcess:pass
    psutil.wait_procs(remaining,timeout=2)


def supervise(owner,lease,command):
    import psutil
    # The supervisor exists only for this foreground command and checks its exact
    # creator identity. Its own creation precedes launching the actual command.
    lease.parent.mkdir(parents=True,exist_ok=True)
    record={'schema_version':1,'supervisor':identity(os.getpid()),'owner':owner,'children':[],'launch_pending':True}
    def store():
        temporary=lease.with_suffix('.tmp')
        temporary.write_text(json.dumps(record),encoding='utf-8');os.replace(temporary,lease)
    store()
    child=None;known={}
    try:
        if same_process(owner) is None:return 125
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        process=psutil.Process(child.pid);known[(process.pid,process.create_time())]=process
        record.update(children=[identity(child.pid)],launch_pending=False);store()
        while True:
            try:
                added=False
                for descendant in process.children(recursive=True):
                    key=(descendant.pid,descendant.create_time())
                    if key not in known:known[key]=descendant;added=True
                if added:
                    record['children']=[{'pid':pid,'created':created} for pid,created in known];store()
            except psutil.NoSuchProcess:pass
            try:
                stdout,stderr=child.communicate(timeout=.1)
                sys.stdout.buffer.write(stdout);sys.stderr.buffer.write(stderr)
                return child.returncode
            except subprocess.TimeoutExpired:
                try:alive=same_process(owner)
                except psutil.AccessDenied:continue  # Uncertain ownership never authorizes a signal.
                if alive is None:
                    owned_cleanup(list(known.values()))
                    return 125
    finally:
        owned_cleanup(list(known.values()))
        if child is not None:
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:pass
        lease.unlink(missing_ok=True)


if __name__=='__main__':
    try:sys.exit(supervise(json.loads(sys.argv[1]),Path(sys.argv[2]),sys.argv[3:]))
    except (OSError,ValueError,KeyError) as error:
        print(f'실행 프로세스 소유권 오류: {error}',file=sys.stderr);sys.exit(125)
