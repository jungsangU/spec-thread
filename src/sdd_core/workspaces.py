"""Work Item file isolation and reviewed, recoverable publication. No Git engine."""
from contextlib import contextmanager
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path
import ctypes
import hashlib
import json
import os
import shutil
import stat
import time
import secrets

from .concurrency import project_lock, runtime_path
from .evidence import content_hash
from .records import merge_changes

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.spec-thread-runtime', '.spec-thread-locks'}
TERMINAL = {'completed', 'failed'}


def load(path, default=None):
    if not path.exists():return deepcopy(default)
    if path.is_symlink():raise ValueError('관리 JSON은 심볼릭 링크를 허용하지 않습니다')
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,sort_keys=True,indent=2)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


def config(root):
    marker=load(root/'.specify/spec-thread.json',{})
    value={'mode':'direct','resolution_attempts':3,'resolution_seconds':300,'copy_exclude':[]}
    setting=marker.get('development',{})
    if not isinstance(setting,dict):raise ValueError('개발 모드 설정 형식 오류')
    value.update(setting)
    if value['mode'] not in ('direct','isolated') or any(type(value[k]) is not int or value[k]<1 for k in ('resolution_attempts','resolution_seconds')):
        raise ValueError('개발 모드 또는 해결 한도 오류')
    if not isinstance(value['copy_exclude'],list):raise ValueError('복제 제외 목록 형식 오류')
    return value


def registry(root):
    data=load(runtime_path(root)/'workspaces.json',{'schema_version':1,'project':str(root.resolve()),'items':{},'queue':[]})
    if data.get('schema_version')!=1 or data.get('project')!=str(root.resolve()) or not isinstance(data.get('items'),dict) or not isinstance(data.get('queue'),list):
        raise ValueError('Workspace Registry 스키마/프로젝트 오류')
    from uuid import UUID
    for identifier,row in data['items'].items():
        if str(UUID(identifier))!=identifier or UUID(identifier).version!=7 or row.get('id')!=identifier or row.get('state') not in ('not_ready','waiting','integrating','resolving','blocked','integrated','discarded'):
            raise ValueError('Workspace 식별자/상태 오류')
    ids=[entry.get('id') for entry in data['queue']]
    if len(set(ids))!=len(ids) or set(ids)-set(data['items']):raise ValueError('통합 대기열 참조 오류')
    return data


def active(root):
    from .records import read_document
    items=registry(root)['items']
    work=read_document(root,'work-items.yaml')['work_items']
    return [row['id'] for row in work if row['status'] not in TERMINAL] + [id for id,row in items.items() if row['state'] not in ('integrated','discarded')]


def mode(root, selected=None, *, runtime_root=None, limits=None, exclude=None):
    with project_lock(root):
        current=config(root)
        if selected is None and runtime_root is None and limits is None and exclude is None:return current
        selected=selected or current['mode']
        requested=dict(current)
        if runtime_root is not None:
            path=Path(runtime_root).expanduser().resolve()
            if path.is_relative_to(root.resolve()) or root.resolve().is_relative_to(path):raise ValueError('Runtime 경로는 원본 밖이어야 합니다')
            if registry(root)['items'] or (runtime_path(root)/'transaction.json').exists():raise ValueError('기존 Runtime 이력이 있어 경로를 변경할 수 없습니다')
            requested['runtime_root']=str(path)
        if limits is not None:
            if any(type(v) is not int or v<1 for v in limits.values()):raise ValueError('해결 한도는 양의 정수입니다')
            requested.update(limits)
        if exclude is not None:requested['copy_exclude']=exclude
        requested['mode']=selected
        if selected not in ('direct','isolated'):raise ValueError('모드는 direct/isolated입니다')
        blockers=list(dict.fromkeys(active(root)))
        changes={key for key in set(requested)|set(current) if requested.get(key)!=current.get(key)}
        if requested!=current and blockers and changes-{'resolution_attempts','resolution_seconds'}:
            raise ValueError(f'활성 Work Item이 있어 모드를 바꿀 수 없습니다: {blockers}')
        if requested!=current:
            marker=load(root/'.specify/spec-thread.json')
            current=requested;marker['development']=current
            save(root/'.specify/spec-thread.json',marker)
        return current


def tree(root, extra=()):
    result={}
    for folder,dirs,files in os.walk(root,followlinks=False):
        parent=Path(folder)
        dirs[:]=[name for name in dirs if name not in EXCLUDED and (parent/name).relative_to(root).as_posix() not in extra]
        for name in dirs+files:
            path=parent/name;relative=path.relative_to(root).as_posix()
            if relative in extra or name in EXCLUDED:continue
            if path.is_symlink():raise ValueError(f'격리 복제 경로에 심볼릭 링크가 있습니다: {relative}')
            if not path.is_file() and not path.is_dir():raise ValueError(f'복제할 수 없는 특수 파일: {relative}')
            if path.is_file():
                if not stat.S_ISREG(path.stat().st_mode):raise ValueError(f'일반 파일이 아닙니다: {relative}')
                result[relative]={'hash':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':stat.S_IMODE(path.stat().st_mode)}
    return result


def clone_file(source, target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if sys_platform()=='darwin':
        lib=ctypes.CDLL(None,use_errno=True)
        if hasattr(lib,'clonefile') and lib.clonefile(os.fsencode(source),os.fsencode(target),0)==0:return 'cow'
    elif os.name=='posix':
        try:
            import fcntl
            with source.open('rb') as src,target.open('xb') as dst:fcntl.ioctl(dst.fileno(),0x40049409,src.fileno())
            shutil.copystat(source,target);return 'cow'
        except OSError:target.unlink(missing_ok=True)
    shutil.copy2(source,target);return 'copy'


def sys_platform():
    import sys
    return sys.platform


def copy_tree(source,target,manifest,extra=()):
    if target.exists():raise ValueError('복제 대상이 이미 존재합니다')
    target.mkdir(parents=True)
    methods={'cow':0,'copy':0}
    for folder,dirs,_ in os.walk(source,followlinks=False):
        parent=Path(folder)
        dirs[:]=[name for name in dirs if name not in EXCLUDED and (parent/name).relative_to(source).as_posix() not in extra]
        for name in dirs:
            path=parent/name
            if path.is_symlink():raise ValueError('복제 디렉터리 심볼릭 링크 거부')
            (target/path.relative_to(source)).mkdir(parents=True,exist_ok=True)
    for name in manifest:
        methods[clone_file(source/name,target/name)]+=1
    for name,mode in sorted(directory_tree(source,extra).items(),key=lambda row:len(Path(row[0]).parts),reverse=True):(target/name).chmod(mode)
    return methods


def directory_tree(root,extra=()):
    result={}
    for folder,dirs,_ in os.walk(root,followlinks=False):
        parent=Path(folder)
        dirs[:]=[name for name in dirs if name not in EXCLUDED and (parent/name).relative_to(root).as_posix() not in extra]
        for name in dirs:
            path=parent/name
            if path.is_symlink():raise ValueError('디렉터리 심볼릭 링크 거부')
            result[path.relative_to(root).as_posix()]=stat.S_IMODE(path.stat().st_mode)
    return result


def digest_tree(manifest,directories=None):
    return content_hash({'files':manifest,'directories':directories or {}})


def reference(root):
    ref=load(root/'.specify/workspace.json')
    if ref is None:return None
    origin=Path(ref['origin']).resolve(strict=True)
    rows=registry(origin)['items'];row=rows.get(ref['work_item'])
    if row is None or row.get('token')!=ref.get('token') or row.get('state') in ('discarded','integrated'):
        raise ValueError('등록되지 않았거나 종료된 Workspace입니다')
    base=runtime_path(origin)/'work'/ref['work_item']
    if any(Path(row[name])!=base/name for name in ('workspace','snapshot','candidate')):raise ValueError('Workspace 경로 규약 불일치')
    allowed=[Path(row['workspace']),Path(row['candidate']),base/'publication']
    allowed.extend(Path(entry['path']) for entry in row.get('retained_candidates',[]) if Path(entry['path']).parent==base/'candidate-history')
    if root.resolve() not in allowed:raise ValueError('Workspace 등록 경로가 일치하지 않습니다')
    base=runtime_path(origin)
    if any(not path.resolve().is_relative_to(base) for path in allowed):raise ValueError('Runtime 밖 Workspace를 허용하지 않습니다')
    scope='workspace' if root.resolve()==Path(row['workspace']) else 'candidate' if root.resolve()==Path(row['candidate']) else 'publication' if root.resolve()==base/'publication' else 'history'
    return {**ref,'scope':scope}


def create(root, identifier):
    from .gates import work_item
    root=root.resolve();_,item=work_item(root,identifier,editable=True)
    if config(root)['mode']!='isolated':raise ValueError('Isolated Mode에서만 Workspace를 생성합니다')
    started=time.monotonic()
    with project_lock(root,'publish'):
        if (runtime_path(root)/'transaction.json').exists():raise ValueError('미완료 통합 트랜잭션을 먼저 복구하세요')
        data=registry(root)
        if identifier in data['items']:return data['items'][identifier]
        settings=config(root);extra=settings['copy_exclude']
        if any(not isinstance(p,str) or Path(p).is_absolute() or '..' in Path(p).parts or p.startswith(('.specify','.agents','.claude','.codex')) for p in extra):
            raise ValueError('제외 경로는 프로젝트 상대 데이터·캐시 경로만 허용합니다')
        before=tree(root,extra);before_dirs=directory_tree(root,extra)
        base=runtime_path(root)/'work'/identifier
        snapshot=base/'snapshot';workspace=base/'workspace';candidate=base/'candidate'
        if base.exists():raise ValueError('미완료 생성 데이터가 있습니다. 원인을 확인하고 명시적으로 정리하세요')
        try:
            methods=copy_tree(root,snapshot,before,extra)
            copy_tree(snapshot,workspace,before)
            if tree(root,extra)!=before or tree(snapshot)!=before or tree(workspace)!=before or directory_tree(root,extra)!=before_dirs or directory_tree(snapshot)!=before_dirs or directory_tree(workspace)!=before_dirs:
                raise ValueError('Snapshot 생성 중 원본 변경 또는 복제 불일치')
            token=secrets.token_hex(32)
            ref={'schema_version':1,'origin':str(root),'work_item':identifier,'token':token}
            save(workspace/'.specify/workspace.json',ref)
            save(base/'snapshot-manifest.json',{'schema_version':1,'files':before,'directories':before_dirs})
            row={'id':identifier,'workspace':str(workspace),'snapshot':str(snapshot),'candidate':str(candidate),'publication':str(base/'publication'),'active_scope':'workspace',
                 'token':token,'state':'not_ready','created_at':time.time(),'snapshot_manifest':str(base/'snapshot-manifest.json'),'file_count':len(before),
                 'copy_methods':methods,'create_seconds':time.monotonic()-started,'attempts':0,
                 'excluded':sorted(EXCLUDED|set(extra)), 'agent_entry':None}
            with project_lock(root):
                data=registry(root);data['items'][identifier]=row
                save(runtime_path(root)/'workspaces.json',data)
            return row
        except BaseException:
            # No registered workspace or evidence exists until successful publication.
            if base.exists():shutil.rmtree(base)
            raise


def enter(root, identifier, plan):
    """Persist verified adapter observations, not a security sandbox claim."""
    with project_lock(root):
        data=registry(root);row=data['items'][identifier];scope=plan.get('scope',row.get('active_scope','workspace'))
        if scope not in ('workspace','candidate'):raise ValueError('진입 Scope 오류')
        workspace=Path(row[scope])
        reference(workspace)
        marker=load(root/'.specify/spec-thread.json')
        required={'same_session','absolute_edit_target','command_cwd','sandbox_access','origin_write_guard','hook_origin_link'}
        if plan.get('agent')!=marker['agent'] or set(plan.get('checks',{}))!=required or any(v is not True for v in plan['checks'].values()):
            raise ValueError('Agent 작업 대상 전환 PoC가 미확인입니다. 원본으로 Fallback하지 않습니다')
        evidence=plan.get('evidence',[])
        if not evidence or any(not isinstance(ref,str) or not(workspace/ref).resolve().is_relative_to(workspace.resolve()) or not(workspace/ref).is_file() for ref in evidence):
            raise ValueError('작업 대상 전환의 실제 로컬 근거가 필요합니다')
        if not isinstance(plan.get('session'),str) or not plan['session'].strip():raise ValueError('현재 Agent Session 식별자가 필요합니다')
        execution=plan.get('execution',{})
        if execution.get('external_resources') not in ('none','isolated','serial') or execution.get('ports') not in ('dynamic','serial'):
            raise ValueError('외부 리소스·포트 격리 확인 또는 순차 검증 설정이 필요합니다')
        row['execution']=execution
        row['agent_entry']={'root':str(workspace),'agent':plan['agent'],'session':plan.get('session'),'checks':plan['checks'],
                            'evidence':{ref:hashlib.sha256((workspace/ref).read_bytes()).hexdigest() for ref in evidence}}
        save(runtime_path(root)/'workspaces.json',data)
        return {'root':str(workspace),'origin':str(root),'work_item':identifier,'sandbox':False}


def changes(base, ours, current):
    return [name for name in sorted(set(base)|set(ours)|set(current)) if base.get(name)!=ours.get(name)]


def text_merge(base,ours,current):
    if ours==base:return current
    if current==base or ours==current:return ours
    try:
        if any(b'\0' in value for value in (base,ours,current)):raise ValueError('binary')
        a=base.decode('utf-8').splitlines(keepends=True)
        edits=[]
        for value,owner in ((ours,0),(current,1)):
            b=value.decode('utf-8').splitlines(keepends=True)
            for tag,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
                if tag!='equal':edits.append((i,j,b[k:l],owner))
        unique=[]
        for edit in edits:
            for prior in unique:
                overlap=max(edit[0],prior[0])<min(edit[1],prior[1]) or edit[0]==edit[1]==prior[0]==prior[1]
                if overlap:
                    if edit[:3]==prior[:3]:break
                    raise ValueError('겹치는 텍스트 변경')
            else:unique.append(edit);continue
        for i,j,lines,_ in sorted(unique,key=lambda e:(e[0],e[1]),reverse=True):a[i:j]=lines
        return ''.join(a).encode('utf-8')
    except UnicodeError as error:raise ValueError('Binary/비 UTF-8 충돌') from error


def candidate(root,identifier,resolution_plan=None):
    from .baseline import BaselineLoader
    import yaml
    data=registry(root);row=data['items'][identifier]
    workspace=Path(row['workspace']);snapshot=Path(row['snapshot']);target=Path(row['candidate'])
    reference(workspace)
    initial=load(runtime_path(root)/'work'/identifier/'snapshot-manifest.json')
    initial_files=initial['files'] if initial else row['manifest']
    initial_dirs=initial['directories'] if initial else row.get('directories',directory_tree(snapshot))
    if tree(snapshot)!=initial_files or directory_tree(snapshot)!=initial_dirs:raise ValueError('최초 Snapshot 무결성 오류')
    original=tree(root,config(root)['copy_exclude']);ours=tree(workspace)
    ours.pop('.specify/workspace.json',None)
    original_dirs=directory_tree(root,config(root)['copy_exclude']);ours_dirs=directory_tree(workspace)
    base_dirs=initial_dirs
    previous=load(runtime_path(root)/'work'/identifier/'preview.json')
    if previous and target.exists() and resolution_plan is None and previous['source']==digest_tree(original,original_dirs) and previous['workspace']==digest_tree(ours,ours_dirs):
        actual=tree(target);actual.pop('.specify/workspace.json',None)
        current=deepcopy(previous);current['candidate']=digest_tree(actual,directory_tree(target))
        current['candidate_manifest']=actual
        current['changed']=sorted(set(current['changed'])|{name for name in set(actual)|set(previous.get('candidate_manifest',{})) if actual.get(name)!=previous.get('candidate_manifest',{}).get(name)})
        save(runtime_path(root)/'work'/identifier/'preview.json',current)
        return current
    cache_file=runtime_path(root)/'work'/identifier/'resolutions.json'
    cached=load(cache_file,{})
    preview_file=runtime_path(root)/'work'/identifier/'preview.json'
    if resolution_plan is not None:
        previous=load(preview_file)
        if previous is None or resolution_plan.get('preview')!=content_hash(previous) or previous['source']!=digest_tree(original,original_dirs) or previous['workspace']!=digest_tree(ours,ours_dirs):
            raise ValueError('충돌 해결 기준이 변경됐습니다. 최신 후보로 다시 검토하세요')
        permitted={item['path'] for item in previous['conflicts']}
        resolutions=resolution_plan.get('resolutions',{})
        if not isinstance(resolutions,dict) or not resolutions:raise ValueError('명시적 해결 파일이 필요합니다')
        if set(resolutions)-permitted:
            from .work_items import check_findings
            check_findings(resolution_plan.get('findings'))
            if not resolution_plan.get('findings') or not resolution_plan.get('reason'):raise ValueError('직접 영향 범위의 추가 수정 근거가 필요합니다')
        if '.specify/baseline/work-items.yaml' in resolutions:raise ValueError('Work Item은 Core 명령으로 수정하세요')
        for name,decision in resolutions.items():
            if not isinstance(decision,dict) or decision.get('action') not in ('write','delete'):raise ValueError('충돌 해결 action 오류')
            triple={'base':initial_files.get(name),'workspace':ours.get(name),'source':original.get(name)}
            entry={'inputs':triple,'action':decision['action']}
            if decision['action']=='write':
                content=safe_path(target,name).read_bytes();hash=hashlib.sha256(content).hexdigest()
                if hash!=decision.get('hash'):raise ValueError('검토한 해결 파일이 바뀌었습니다')
                output=runtime_path(root)/'work'/identifier/'resolved'/hash
                output.parent.mkdir(parents=True,exist_ok=True)
                if not output.exists():output.write_bytes(content)
                entry['hash']=hash;entry['mode']=stat.S_IMODE(safe_path(target,name).stat().st_mode)
            cached[name]=entry
        save(cache_file,cached)
        with project_lock(root):
            data=registry(root);pending=data['items'][identifier].get('unresolved_candidate_paths',{})
            for name in resolutions:pending.pop(name,None)
            save(runtime_path(root)/'workspaces.json',data)
    if target.exists():checkpoint_candidate(root,identifier)
    if target.exists() and previous and (previous['source']!=digest_tree(original,original_dirs) or previous['workspace']!=digest_tree(ours,ours_dirs)):
        actual=tree(target);actual.pop('.specify/workspace.json',None)
        baseline=previous.get('generated_manifest',previous.get('candidate_manifest',{}))
        evidence_paths=set()
        try:
            from .gates import work_item
            _,old_item=work_item(target,identifier)
            for gate in old_item.get('gate_revisions',[{}])[-1].get('gates',[]):evidence_paths.update(ref.partition('#')[0] for ref in gate['evidence'])
        except (ValueError,OSError):pass
        dirty=[name for name in set(actual)|set(baseline) if actual.get(name)!=baseline.get(name) and name!='.specify/baseline/work-items.yaml' and not name.startswith('docs/sdd/evidence/'+identifier+'/') and name not in evidence_paths]
        if dirty:
            key=digest_tree(actual,directory_tree(target)).split(':')[1]
            archive=runtime_path(root)/'work'/identifier/'candidate-history'/key
            archive.parent.mkdir(parents=True,exist_ok=True)
            if not archive.exists():target.rename(archive)
            else:remove_owned_tree(root,target)
            with project_lock(root):
                data=registry(root);item=data['items'][identifier]
                record={'path':str(archive),'paths':dirty}
                if record not in item.setdefault('retained_candidates',[]):item['retained_candidates'].append(record)
                unresolved=item.setdefault('unresolved_candidate_paths',{})
                for name in dirty:unresolved[name]=str(archive)
                save(runtime_path(root)/'workspaces.json',data)
    if target.exists():remove_owned_tree(root,target)
    copy_tree(root,target,original,config(root)['copy_exclude'])
    conflicts=[];changed=sorted(set(changes(initial_files,ours,original))|set(cached))
    removed_dirs=[]
    for name in sorted(set(base_dirs)|set(ours_dirs)):
        if base_dirs.get(name)==ours_dirs.get(name):continue
        if original_dirs.get(name)!=base_dirs.get(name) and original_dirs.get(name)!=ours_dirs.get(name):
            conflicts.append({'path':name+'/','reason':'디렉터리 변경 충돌'});continue
        if name not in ours_dirs:removed_dirs.append(name)
        elif (target/name).is_file():conflicts.append({'path':name+'/','reason':'파일/디렉터리 형식 충돌'})
        else:(target/name).mkdir(parents=True,exist_ok=True)
    for name in changed:
        if (target/name).is_dir():
            conflicts.append({'path':name,'reason':'디렉터리를 파일로 조용히 대체하지 않습니다'});continue
        old=initial_files.get(name);mine=ours.get(name);latest=original.get(name)
        if name.startswith('.git/') or name in ('.specify/spec-thread.json','.specify/sdd-core') or '/skills/' in name:
            conflicts.append({'path':name,'reason':'설치/Core/Skill 변경은 통합 대상이 아닙니다'});continue
        resolved=cached.get(name)
        if resolved and resolved['inputs']=={'base':old,'workspace':mine,'source':latest}:
            if resolved['action']=='delete':(target/name).unlink(missing_ok=True)
            else:
                content=(runtime_path(root)/'work'/identifier/'resolved'/resolved['hash']).read_bytes()
                if hashlib.sha256(content).hexdigest()!=resolved['hash']:raise ValueError('해결 파일 무결성 오류')
                (target/name).parent.mkdir(parents=True,exist_ok=True);(target/name).write_bytes(content);(target/name).chmod(resolved['mode'])
            continue
        if latest==old or latest==mine:
            if mine is None:
                (target/name).unlink(missing_ok=True)
            else:
                (target/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(workspace/name,target/name)
            continue
        if old is None or mine is None or latest is None:
            conflicts.append({'path':name,'reason':'생성/삭제/수정 충돌'});continue
        try:
            if mine['mode']!=old['mode'] and latest['mode']!=old['mode'] and mine['mode']!=latest['mode']:
                raise ValueError('파일 권한 변경 충돌')
            merged_mode=mine['mode'] if mine['mode']!=old['mode'] else latest['mode']
            base_bytes=(snapshot/name).read_bytes();our_bytes=(workspace/name).read_bytes();latest_bytes=(root/name).read_bytes()
            if name in ('.specify/baseline/features.yaml','.specify/baseline/work-items.yaml','.specify/baseline/source-map.yaml','.specify/baseline/verification.yaml'):
                merged=merge_changes(*[yaml.load(value,Loader=BaselineLoader) for value in (base_bytes,our_bytes,latest_bytes)])
                (target/name).write_text(yaml.safe_dump(merged,allow_unicode=True,sort_keys=False),encoding='utf-8')
            else:(target/name).write_bytes(text_merge(base_bytes,our_bytes,latest_bytes))
            (target/name).chmod(merged_mode)
        except ValueError as error:conflicts.append({'path':name,'reason':str(error)})
    for name in sorted(removed_dirs,key=lambda value:len(Path(value).parts),reverse=True):
        if (target/name).is_dir():
            try:(target/name).rmdir()
            except OSError:conflicts.append({'path':name+'/', 'reason':'최신 원본의 디렉터리 내용 보존: 명시적 해결 필요'})
    for name,mode in ours_dirs.items():
        if mode!=base_dirs.get(name) and (target/name).is_dir():(target/name).chmod(mode)
    save(target/'.specify/workspace.json',load(workspace/'.specify/workspace.json'))
    restore_candidate_history(root,identifier)
    from .gates import work_item
    _,workspace_item=work_item(workspace,identifier)
    save(runtime_path(root)/'work'/identifier/'candidate-inputs.json',{'workspace_item':content_hash(workspace_item),'workspace_files':ours})
    manifest=tree(target);manifest.pop('.specify/workspace.json',None)
    latest_row=registry(root)['items'][identifier]
    conflicts.extend({'path':name,'reason':'보존된 이전 후보의 변경 의도 검토 필요','retained_candidate':path} for name,path in latest_row.get('unresolved_candidate_paths',{}).items())
    with project_lock(root):
        data=registry(root);data['items'][identifier]['active_scope']='candidate';save(runtime_path(root)/'workspaces.json',data)
    preview={'development_root':str(target),'retained_candidates':latest_row.get('retained_candidates',[]),'work_item':identifier,'source_manifest':original,'source_directories':original_dirs,'source':digest_tree(original,original_dirs),'workspace':digest_tree(ours,ours_dirs),
            'generated_manifest':manifest,'candidate_manifest':manifest,'candidate':digest_tree(manifest,directory_tree(target)),'changed':changed,'conflicts':conflicts,
            'source_changes':[name for name in sorted(set(original)|set(initial_files)) if original.get(name)!=initial_files.get(name)]}
    save(preview_file,preview)
    return preview


def queue(root,identifier):
    ready(root,identifier)
    with project_lock(root):
        data=registry(root);row=data['items'][identifier]
        if row['state'] in ('integrated','discarded'):raise ValueError('종료 Workspace입니다')
        if identifier not in [entry['id'] for entry in data['queue']]:
            data['queue'].append({'id':identifier,'queued_at':time.time()})
        row['state']='waiting';save(runtime_path(root)/'workspaces.json',data)
        return {'position':[entry['id'] for entry in data['queue']].index(identifier)+1,'queue':data['queue']}


def dequeue(root,identifier,state,reason=None):
    with project_lock(root):
        data=registry(root);data['queue']=[entry for entry in data['queue'] if entry['id']!=identifier]
        data['items'][identifier].update(state=state,reason=reason)
        save(runtime_path(root)/'workspaces.json',data)


def safe_path(root,name):
    path=root/name
    if Path(name).is_absolute() or '..' in Path(name).parts or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('원본 경로 탈출')
    parent=path
    while parent!=root:
        if parent.is_symlink():raise ValueError('원본 경로에 심볼릭 링크가 있습니다')
        parent=parent.parent
    return path


def node_state(path):
    if not path.exists():return None
    if path.is_symlink():raise ValueError('트랜잭션 경로 링크 거부')
    mode=stat.S_IMODE(path.stat().st_mode)
    if path.is_dir():return {'kind':'directory','mode':mode}
    if path.is_file():return {'kind':'file','mode':mode,'hash':hashlib.sha256(path.read_bytes()).hexdigest()}
    raise ValueError('트랜잭션 특수 파일 거부')


def apply_node(path,state,source=None):
    if state is None:
        if path.is_dir():path.rmdir()
        else:path.unlink(missing_ok=True)
    elif state['kind']=='directory':
        path.mkdir(parents=True,exist_ok=True);path.chmod(state['mode'])
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.specthread-'+secrets.token_hex(8))
        try:shutil.copy2(source,temporary);os.replace(temporary,path);path.chmod(state['mode'])
        finally:temporary.unlink(missing_ok=True)


def recover(root):
    journal_path=runtime_path(root)/'transaction.json'
    with project_lock(root,'integration',timeout=.1),project_lock(root,'publish'),project_lock(root):
        journal=load(journal_path)
        if not journal:return {'status':'clean'}
        if journal['phase']=='committed':
            journal_path.unlink();return {'status':'committed'}
        if journal.get('schema_version')!=1 or Path(journal['backup'])!=runtime_path(root)/'backup'/journal['work_item']:
            raise ValueError('트랜잭션 Journal 경로/스키마 불일치')
        for action in reversed(journal['actions']):
            path=safe_path(root,action['path']);current=node_state(path)
            if current==action['before']:continue
            if current!=action['after']:
                raise ValueError(f'복구 중 외부 변경 발견, 사용자 판단 필요: {action["path"]}')
            apply_node(path,action['before'],Path(journal['backup'])/action['path'])
        data=journal['registry_before']
        if journal['work_item'] in data['items']:data['items'][journal['work_item']]['state']='blocked'
        save(runtime_path(root)/'workspaces.json',data);journal_path.unlink()
        return {'status':'recovered','work_item':journal['work_item']}


def publish(root,identifier,expected, *, fault=None, source_manifest=None,source_directories=None):
    row=registry(root)['items'][identifier];source=Path(row.get('publication','')) if row.get('publication') and Path(row['publication']).is_dir() else Path(row['candidate'])
    with project_lock(root,'publish'),project_lock(root):
        current=tree(root,config(root)['copy_exclude']);current_dirs=directory_tree(root,config(root)['copy_exclude'])
        if digest_tree(current,current_dirs)!=expected:
            changed=[name for name in set(current)|set(source_manifest or {}) if current.get(name)!=(source_manifest or {}).get(name)]
            if source_manifest is None or changed!=['.specify/baseline/work-items.yaml'] or current_dirs!=source_directories:
                raise ValueError('원본이 변경됐습니다. 최신 원본으로 재검토하세요')
            import yaml
            from .baseline import BaselineLoader
            path=source/'.specify/baseline/work-items.yaml'
            base_doc=load(runtime_path(root)/'source-work-items.json')
            if base_doc is None:raise ValueError('통합 기준 관리 스냅샷이 없습니다')
            merged=merge_changes(base_doc,yaml.load(path.read_text(),Loader=BaselineLoader),yaml.load((root/'.specify/baseline/work-items.yaml').read_text(),Loader=BaselineLoader))
            path.write_text(yaml.safe_dump(merged,allow_unicode=True,sort_keys=False),encoding='utf-8')
        final=tree(source);final.pop('.specify/workspace.json',None);final_dirs=directory_tree(source)
        backup=runtime_path(root)/'backup'/identifier;backup.mkdir(parents=True,exist_ok=True)
        actions=[]
        directory_creation_mode=0o777 if os.name=='nt' else 0o755
        for name in sorted(set(final_dirs)-set(current_dirs),key=lambda value:len(Path(value).parts)):
            actions.append({'path':name,'before':None,'after':{'kind':'directory','mode':directory_creation_mode}})
        for name in sorted(set(current)|set(final)):
            if current.get(name)==final.get(name):continue
            path=safe_path(root,name);before=node_state(path)
            if before is not None and before['kind']=='file':
                (backup/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/name)
            actions.append({'path':name,'before':before,'after':node_state(source/name)})
        for name in sorted(set(current_dirs)-set(final_dirs),key=lambda value:len(Path(value).parts),reverse=True):
            actions.append({'path':name,'before':{'kind':'directory','mode':current_dirs[name]},'after':None})
        for name,mode in sorted(final_dirs.items(),key=lambda row:len(Path(row[0]).parts),reverse=True):
            before=current_dirs.get(name,directory_creation_mode)
            if before!=mode:actions.append({'path':name,'before':{'kind':'directory','mode':before},'after':{'kind':'directory','mode':mode}})
        journal_path=runtime_path(root)/'transaction.json'
        if journal_path.exists():raise ValueError('미완료 트랜잭션을 먼저 복구하세요')
        journal={'schema_version':1,'phase':'applying','work_item':identifier,'backup':str(backup),'actions':actions,'registry_before':registry(root)}
        save(journal_path,journal)
        for index,action in enumerate(actions):
            path=safe_path(root,action['path'])
            if node_state(path)!=action['before']:raise ValueError('반영 직전 외부 변경 발견')
            apply_node(path,action['after'],source/action['path'])
            if fault:fault(index)
        if tree(root,config(root)['copy_exclude'])!=final or directory_tree(root,config(root)['copy_exclude'])!=final_dirs:
            raise ValueError('반영 후 정합성 불일치')
        data=registry(root);data['items'][identifier].update(state='integrated',integrated_at=time.time(),
            integration_seconds=time.time()-data['items'][identifier].get('integration_started_at',time.time()))
        data['queue']=[entry for entry in data['queue'] if entry['id']!=identifier]
        save(runtime_path(root)/'workspaces.json',data)
        journal['phase']='committed';save(journal_path,journal);journal_path.unlink()


def _integrate_once(root,identifier,plan=None):
    """One synchronous worker; no scheduler or background agent is started."""
    row=registry(root)['items'][identifier]
    if row['agent_entry'] is None:raise ValueError('확인된 Agent 작업 대상 전환 기록이 필요합니다')
    queue(root,identifier)
    with project_lock(root,'integration',timeout=.1):
        data=registry(root)
        if data['queue'][0]['id']!=identifier:return {'status':'waiting','queue':data['queue']}
        with project_lock(root):
            data=registry(root);item=data['items'][identifier]
            item['state']='integrating';item['integration_started_at']=time.time()
            item['wait_seconds']=time.time()-data['queue'][0]['queued_at']
            save(runtime_path(root)/'workspaces.json',data)
        resolution_started=time.monotonic()
        preview=candidate(root,identifier)
        from .records import read_document
        save(runtime_path(root)/'source-work-items.json',dict(read_document(root,'work-items.yaml')))
        if preview['conflicts'] or plan is None:
            if preview['conflicts']:
                with project_lock(root):
                    data=registry(root);item=data['items'][identifier]
                    fingerprint=content_hash({'conflicts':preview['conflicts'],'source':preview['source'],'workspace':preview['workspace']})
                    same=item.get('last_failure')==fingerprint
                    item['attempts']+=1;item['last_failure']=fingerprint
                    item['resolution_seconds']=item.get('resolution_seconds',0)+time.monotonic()-resolution_started
                    reason='no progress' if same else 'conflict'
                    if item['attempts']>=config(root)['resolution_attempts'] or item['resolution_seconds']>=config(root)['resolution_seconds']:
                        reason='resolution limit'
                    save(runtime_path(root)/'workspaces.json',data)
            else:reason='impact review'
            dequeue(root,identifier,'blocked',reason)
            return {'status':'blocked','preview':preview}
        if plan.get('preview')!=content_hash(preview):
            dequeue(root,identifier,'blocked','stale review');raise ValueError('통합 후보가 바뀌었습니다. 새 영향 검토가 필요합니다')
        from .work_items import check_findings
        check_findings(plan.get('findings'))
        if not plan.get('findings'):raise ValueError('직접·간접 영향 검토 근거가 필요합니다')
        from .gates import work_item,execute_gate,gate_status
        target=Path(row['candidate']);_,item=work_item(target,identifier,editable=True)
        fingerprint=content_hash({'preview':preview,'execution':registry(root)['items'][identifier].get('execution')})
        latest=registry(root)['items'][identifier]
        exhausted=latest.get('attempts',0)>=config(root)['resolution_attempts'] or latest.get('resolution_seconds',0)>=config(root)['resolution_seconds']
        if latest.get('verification_failure')==fingerprint or exhausted:
            resume=content_hash({'work_item':identifier,'failure':latest.get('verification_failure'),'attempts':latest.get('attempts',0),'preview':preview})
            if plan.get('resume_confirm')!=resume:
                dequeue(root,identifier,'blocked','no progress' if not exhausted else 'resolution limit')
                return {'status':'blocked','reason':'Explicit user decision needed before another bounded attempt','resume_hash':resume,'preview':preview}
            with project_lock(root):
                data=registry(root);data['items'][identifier].update(attempts=0,resolution_seconds=0)
                save(runtime_path(root)/'workspaces.json',data)
        # Reuse valid current results; run only the existing affected command Gates.
        try:
            for status in gate_status(target,item,'complete'):
                if status['status']!='PASS':
                    result=execute_gate(target,identifier,status['id'])
                    if result['status']!='PASS':raise ValueError('통합 필수 Gate 실패')
        except BaseException:
            with project_lock(root):
                data=registry(root);failed=data['items'][identifier]
                failed['verification_failure']=fingerprint;failed['attempts']+=1
                save(runtime_path(root)/'workspaces.json',data)
            dequeue(root,identifier,'blocked','verification failure');raise
        from .cli import complete_work
        publication=runtime_path(root)/'work'/identifier/'publication'
        if publication.exists():remove_owned_tree(root,publication)
        copy_tree(target,publication,tree(target))
        target=publication
        from .records import write_document
        document=read_document(target,'work-items.yaml')
        final_item=next(row for row in document['work_items'] if row['id']==identifier)
        final_item['integration']={'state':'integrated','source_snapshot':preview['source'],
                                   'wait_seconds':registry(root)['items'][identifier].get('wait_seconds',0)}
        write_document(target,'work-items.yaml',document)
        completion=target/'.specify/integration-completion.json'
        save(completion,plan['completion'])
        try:
            complete_work(target,identifier,completion)
        finally:completion.unlink(missing_ok=True)
        try:publish(root,identifier,preview['source'],source_manifest=preview['source_manifest'],source_directories=preview['source_directories'])
        except BaseException:
            if (runtime_path(root)/'transaction.json').exists():recover(root)
            dequeue(root,identifier,'blocked','publication failure');raise
        data=registry(root);finished=data['items'][identifier]
        remove_owned_tree(root,runtime_path(root)/'work'/identifier)
        backup=runtime_path(root)/'backup'/identifier
        if backup.exists():shutil.rmtree(backup)
        return {'status':'integrated','work_item':identifier,'origin':str(root)}


def discard(root,identifier,confirm):
    with project_lock(root,'worker-'+identifier,timeout=.1),project_lock(root,'integration'),project_lock(root,'publish'),project_lock(root):
        from .records import read_document,write_document
        recover_processes(root,identifier)
        data=registry(root);row=data['items'][identifier]
        if row['state'] in ('integrated','discarded'):raise ValueError('종료 Workspace입니다')
        current_work=read_document(root,'work-items.yaml')
        original=next(item for item in current_work['work_items'] if item['id']==identifier)
        approval={'workspace':row,'inputs':tree(Path(row[row.get('active_scope','workspace')])),'origin_work_item':original}
        if confirm!=content_hash(approval):return {'approval_hash':content_hash(approval),'workspace':approval}
        if (runtime_path(root)/'transaction.json').exists():raise ValueError('트랜잭션 복구가 먼저 필요합니다')
        workspace=Path(row[row.get('active_scope','workspace')])
        capsule=read_document(workspace,'work-items.yaml')
        evidence=workspace/'docs/sdd/evidence'/identifier
        if evidence.exists():
            for source in evidence.rglob('*'):
                if source.is_symlink():raise ValueError('증거 심볼릭 링크 거부')
                if source.is_file():
                    target=safe_path(root,source.relative_to(workspace).as_posix())
                    target.parent.mkdir(parents=True,exist_ok=True)
                    if target.exists() and target.read_bytes()!=source.read_bytes():raise ValueError('증거 보존 충돌')
                    if not target.exists():shutil.copy2(source,target)
        record_ref=f'docs/sdd/evidence/{identifier}/discarded-work-item.json'
        save(safe_path(root,record_ref),{'schema_version':1,'work_item':next(item for item in capsule['work_items'] if item['id']==identifier),
                                      'feature_context':read_document(workspace,'features.yaml')})
        original.update(status='failed',integration={'state':'discarded','reason':'explicit user discard','history':record_ref})
        write_document(root,'work-items.yaml',current_work)
        row.update(state='discarded',discarded_at=time.time(),history=record_ref)
        data['queue']=[entry for entry in data['queue'] if entry['id']!=identifier]
        save(runtime_path(root)/'workspaces.json',data)
        remove_owned_tree(root,runtime_path(root)/'work'/identifier)
        return {'status':'discarded','work_item':identifier,'history':record_ref}


def guard(root, operation, identifier=None):
    """Cooperative Core guard; native file tools must obey the adapter scope."""
    ref=reference(root)
    if ref:
        if operation=='complete':raise ValueError('Isolated 작업은 원본 통합 성공 전 completed로 전환할 수 없습니다')
        row=registry(Path(ref['origin']))['items'][ref['work_item']]
        if row['agent_entry'] is None:
            raise ValueError('작업 대상 전환 검증 전 Workspace 개발을 차단합니다')
        session=os.environ.get('SPECTHREAD_AGENT_SESSION') or os.environ.get('CODEX_THREAD_ID')
        if session and session!=row['agent_entry']['session']:raise ValueError('다른 Agent Session입니다. 작업 대상 전환을 다시 확인하세요')
        readonly={'status','validate','fingerprint','version-check','preflight','develop-check','office-approval','uuid'}
        if operation not in readonly:
            expected=Path(row[row.get('active_scope','workspace')])
            if ref['scope'] in ('history','publication') or root.resolve()!=expected or row['agent_entry'].get('root')!=str(expected):
                raise ValueError('현재 개발 대상이 변경됐습니다. 등록된 개발 경로의 도구·권한을 확인한 뒤 workspace enter를 다시 수행하세요')
        if identifier is not None and identifier!=ref['work_item']:
            raise ValueError('다른 Work Item을 Workspace에서 수정할 수 없습니다')
        return
    if config(root)['mode']=='isolated':
        if operation=='reconcile' and not active(root):return
        if identifier is not None:
            from .records import read_document
            item=next((row for row in read_document(root,'work-items.yaml')['work_items'] if row['id']==identifier),None)
            if item and item.get('kind')=='reconciliation' and operation in ('transition','gates','gate-run','gate-refresh','stage-check','complete'):
                return
    if config(root)['mode']=='isolated' and not active(root) and operation in ('analysis-record','feature-register','baseline-write','source-map','scaffold'):return
    if config(root)['mode']=='isolated' and operation not in ('start','mode','workspace','status','validate','version-check','preflight','develop-check','fingerprint','office-approval','uuid'):
        raise ValueError('Isolated Mode 원본 직접 개발을 차단합니다. 등록 Workspace를 사용하세요')


def update_blockers(root):
    if (root/'.specify/workspace.json').exists():return ['Workspace 내부 Core 업데이트 금지']
    data=registry(root)
    return [id for id,row in data['items'].items() if row['state'] not in ('integrated','discarded')] + (['transaction'] if (runtime_path(root)/'transaction.json').exists() else [])


@contextmanager
def execution(root, command):
    from contextlib import ExitStack
    ref=reference(root)
    if ref is None:
        yield None
        return
    origin=Path(ref['origin']);recover_processes(origin,ref['work_item']);row=registry(origin)['items'][ref['work_item']]
    if row.get('agent_entry') is None:raise ValueError('Agent 작업 대상 전환이 미확인입니다')
    plan=row.get('execution',{})
    if plan.get('external_resources') not in ('none','isolated','serial') or plan.get('ports') not in ('dynamic','serial'):
        raise ValueError('외부 리소스·포트 격리 미확인: 병렬 검증 차단')
    if any(str(origin) in arg for arg in command):
        raise ValueError('독립 개발 명령이 원본 경로를 참조합니다')
    env=dict(os.environ)
    for name in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR'):env.pop(name,None)
    env['GIT_CEILING_DIRECTORIES']=str(root.parent)
    temp=runtime_path(origin)/'work'/ref['work_item']/'temp';temp.mkdir(parents=True,exist_ok=True)
    env.update(TMPDIR=str(temp),TMP=str(temp),TEMP=str(temp),SPECTHREAD_WORK_ITEM=ref['work_item'],
               SPECTHREAD_WORKSPACE=str(root),SPECTHREAD_ORIGIN=str(origin))
    additions=plan.get('env',{})
    if not isinstance(additions,dict) or any(not isinstance(k,str) or not isinstance(v,str) or k in ('HOME','PATH','PYTHONPATH','TMPDIR','TMP','TEMP') for k,v in additions.items()):
        raise ValueError('격리 환경 변수 설정을 확인하세요')
    env.update(additions)
    with ExitStack() as stack:
        stack.enter_context(project_lock(origin,'execution-'+ref['work_item']))
        if plan['external_resources']=='serial' or plan['ports']=='serial':
            stack.enter_context(project_lock(origin,'external-test',timeout=300))
        yield env


def prune_dead_workers(root, exclude=None):
    # An abandoned kernel ownership lock proves command-owner termination.
    # Entries without a worker remain Work Item-owned; absence is not guessed death.
    with project_lock(root):
        data=registry(root);changed=False
        for entry in list(data['queue']):
            if entry['id']==exclude or not entry.get('worker'):continue
            try:
                with project_lock(root,'worker-'+entry['id'],timeout=.02):
                    data['queue'].remove(entry)
                    data['items'][entry['id']].update(state='blocked',reason='terminated integration worker')
                    changed=True
            except ValueError:pass
        if changed:save(runtime_path(root)/'workspaces.json',data)


def integrate(root,identifier,plan=None, *, wait=False):
    ready(root,identifier)
    with project_lock(root,'worker-'+identifier,timeout=.1):
        prune_dead_workers(root,identifier)
        token=secrets.token_hex(16)
        with project_lock(root):
            data=registry(root)
            if identifier not in [entry['id'] for entry in data['queue']]:data['queue'].append({'id':identifier,'queued_at':time.time()})
            data['items'][identifier]['state']='waiting'
            for entry in data['queue']:
                if entry['id']==identifier:entry['worker']=token
            save(runtime_path(root)/'workspaces.json',data)
        try:
            while True:
                try:result=_integrate_once(root,identifier,plan)
                except ValueError as error:
                    if '프로젝트 integration Lock' not in str(error):raise
                    result={'status':'waiting','work_item':identifier}
                if not wait or result['status']!='waiting':return result
                time.sleep(.1)
                prune_dead_workers(root,identifier)
        except BaseException:
            if not (runtime_path(root)/'transaction.json').exists():
                dequeue(root,identifier,'blocked','integration interrupted')
            raise
        finally:
            with project_lock(root):
                data=registry(root)
                for entry in data['queue']:
                    if entry['id']==identifier:entry.pop('worker',None)
                save(runtime_path(root)/'workspaces.json',data)


def retain_evidence(root,identifier,result):
    if reference(root) is None:return
    from .evidence import resolve_evidence
    retained={}
    for ref,expected in result.get('evidence',{}).items():
        source=resolve_evidence(root,ref.partition('#')[0])
        content=source.read_bytes()
        if hashlib.sha256(content).hexdigest()!=expected:raise ValueError('증거 보존 중 입력 변경')
        name=f'docs/sdd/evidence/{identifier}/objects/{expected}'
        target=safe_path(root,name);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=content:raise ValueError('보존 증거 무결성 충돌')
        if not target.exists():target.write_bytes(content)
        retained[ref]=name
    if retained:result['retained_evidence']=retained



def inspect_runtime(root):
    data=registry(root);base=runtime_path(root)
    logical=allocated=0
    if base.is_dir():
        for folder,dirs,files in os.walk(base,followlinks=False):
            for name in dirs+files:
                path=Path(folder)/name
                if path.is_symlink():raise ValueError('Runtime 심볼릭 링크 거부')
                if path.is_file():
                    info=path.stat();logical+=info.st_size;allocated+=getattr(info,'st_blocks',0)*512
    return {'runtime':str(base),'logical_bytes':logical,'reported_allocated_bytes':allocated,
            'physical_unique_bytes':None,'registry':data,
            'recovery_required':(base/'transaction.json').exists()}


def cleanup(root,confirm=None):
    with project_lock(root,'integration'),project_lock(root,'publish'),project_lock(root):
        data=registry(root);base=runtime_path(root)
        if (base/'transaction.json').exists():raise ValueError('미완료 트랜잭션을 먼저 복구하세요')
        candidates=[]
        folder=base/'work'
        if folder.is_dir():
            for path in folder.iterdir():
                if path.is_symlink():raise ValueError('정리 경로 심볼릭 링크 거부')
                row=data['items'].get(path.name)
                if path.is_dir() and (row is None or row['state'] in ('integrated','discarded')):
                    candidates.append(str(path))
        preview={'paths':sorted(candidates),'registry':content_hash(data)}
        if confirm!=content_hash(preview):return {'approval_hash':content_hash(preview),'cleanup':preview}
        for name in candidates:shutil.rmtree(name)
        return {'status':'cleaned','paths':candidates}


def start_discovery(root,identifier):
    from .baseline import validate
    from .records import read_document,write_document
    with project_lock(root):
        validate(root)
        if config(root)['mode']!='isolated':raise ValueError('격리 Discovery는 Isolated Mode에서만 사용합니다')
        document=read_document(root,'work-items.yaml')
        if any(item['id']==identifier for item in document['work_items']):raise ValueError('중복 Work Item')
        document['work_items'].append({'id':identifier,'status':'pending','declared_features':[],
                                       'actual_features':[],'related_work_items':[],'discovery_pending':True})
        write_document(root,'work-items.yaml',document)


def bind_discovery(root,identifier,features,reason):
    from .gates import work_item
    from .analysis import develop_check
    from .baseline import nonempty
    from .records import write_document
    with project_lock(root):
        ref=reference(root)
        if ref is None or ref['work_item']!=identifier:raise ValueError('등록 Workspace의 Discovery 작업만 연결합니다')
        document,item=work_item(root,identifier,editable=True)
        if item['status']!='pending' or item['declared_features'] or not item.get('discovery_pending'):
            raise ValueError('최초 Discovery 범위 연결 조건이 아닙니다')
        nonempty(reason,'최초 Feature 연결 근거')
        if not features:raise ValueError('확정 Feature가 필요합니다')
        develop_check(root,features)
        item.update(declared_features=list(dict.fromkeys(features)),discovery_pending=False,
                    scope_changes=[{'from':[],'to':features,'reason':reason}])
        write_document(root,'work-items.yaml',document)



def ready(root,identifier):
    from .gates import work_item,require_gates
    row=registry(root)['items'][identifier]
    if row.get('agent_entry') is None:raise ValueError('Agent 진입 검증이 필요합니다')
    if row['state'] in ('integrated','discarded'):raise ValueError('종료된 Workspace입니다')
    _,item=work_item(Path(row[row.get('active_scope','workspace')]),identifier,editable=True)
    if item['status']!='in_progress':raise ValueError('진행 중인 개발을 먼저 검증하세요')
    require_gates(Path(row[row.get('active_scope','workspace')]),item,'complete')



def recover_processes(root,identifier=None):
    import psutil
    from .processes import same_process,owned_cleanup
    data=registry(root)
    for id,row in data['items'].items():
        if identifier is not None and id!=identifier:continue
        folder=runtime_path(root)/'work'/id/'temp'
        for lease in folder.glob('process-*.json'):
            if lease.is_symlink():raise ValueError('프로세스 소유권 파일 링크 거부')
            state=load(lease)
            try:supervisor=same_process(state['supervisor'])
            except psutil.AccessDenied:raise ValueError('프로세스 생존 미확인: 자동 정리 차단')
            if supervisor is not None:
                if identifier is not None:raise ValueError('동일 Work Item 실행 프로세스가 남아 있습니다')
                continue
            if state.get('launch_pending'):raise ValueError('프로세스 시작 중 종료되어 소유권이 미확인입니다. 사용자 확인 필요')
            owned=[]
            for expected in state.get('children',[]):
                try:process=same_process(expected)
                except psutil.AccessDenied:raise ValueError('하위 프로세스 소유권 미확인')
                if process is not None:owned.append(process)
            owned_cleanup(owned)
            lease.unlink(missing_ok=True)


def execution_context(root):
    ref=reference(root)
    if ref is None:return None
    from . import __version__
    settings=registry(Path(ref['origin']))['items'][ref['work_item']].get('execution',{})
    actual=Path(registry(Path(ref['origin']))['items'][ref['work_item']]['candidate']) if ref['scope']=='publication' else root.resolve()
    return {'core':__version__,'plan':content_hash(settings),
            'root':None if settings.get('relocatable') is True else str(actual)}



def checkpoint_candidate(root,identifier):
    from .gates import work_item
    row=registry(root)['items'][identifier];target=Path(row['candidate'])
    if not (target/'.specify/workspace.json').exists():return
    reference(target)
    _,item=work_item(target,identifier)
    inputs=load(runtime_path(root)/'work'/identifier/'candidate-inputs.json',{})
    record={'schema_version':1,'workspace_item':inputs.get('workspace_item'),'workspace_files':inputs.get('workspace_files',{}),'item':item,'evidence':{}}
    for history in item.get('gate_results',{}).values():
        for result in history:
            refs=[*result.get('evidence',{}),*result.get('retained_evidence',{}).values()]
            for ref in refs:
                source=safe_path(target,ref.partition('#')[0])
                if not source.is_file():continue
                content=source.read_bytes();hash=hashlib.sha256(content).hexdigest()
                destination=runtime_path(root)/'work'/identifier/'verification-objects'/hash
                destination.parent.mkdir(parents=True,exist_ok=True)
                if not destination.exists():destination.write_bytes(content)
                record['evidence'][ref.partition('#')[0]]=hash
    save(runtime_path(root)/'work'/identifier/'verification-history.json',record)


def restore_candidate_history(root,identifier):
    from .gates import work_item
    from .records import write_document
    from .evidence import current_result,verify_evidence
    row=registry(root)['items'][identifier];target=Path(row['candidate'])
    saved=load(runtime_path(root)/'work'/identifier/'verification-history.json')
    if not saved:return
    old=saved['item']
    if old['id']!=identifier:raise ValueError('다른 Work Item 검증 이관 거부')
    current_workspace_files=tree(Path(row['workspace']))
    for name,expected in saved['evidence'].items():
        if current_workspace_files.get(name)!=saved.get('workspace_files',{}).get(name):continue
        destination=safe_path(target,name)
        if destination.exists():continue
        content=(runtime_path(root)/'work'/identifier/'verification-objects'/expected).read_bytes()
        if hashlib.sha256(content).hexdigest()!=expected:raise ValueError('보존 검증 증거 무결성 오류')
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content)
    document,item=work_item(target,identifier)
    _,workspace_item=work_item(Path(row['workspace']),identifier)
    if saved['workspace_item']==content_hash(workspace_item):
        for field in ('verification','declared_features','actual_features','scope_changes','gate_revisions','gate_results'):
            if field in old:item[field]=deepcopy(old[field])
    else:
        previous=old.get('gate_revisions',[])
        current=item.get('gate_revisions',[])
        if previous and current:
            old_revision=previous[-1];new_revision=current[-1]
            old_defs={gate['id']:gate for gate in old_revision['gates']}
            try:valid_basis=verify_evidence(target,list(old_revision['basis']))==old_revision['basis']
            except (ValueError,OSError):valid_basis=False
            if valid_basis:
                for gate in new_revision['gates']:
                    prior=old_defs.get(gate['id']);runs=old.get('gate_results',{}).get(gate['id'],[])
                    if prior!=gate or not runs or current_result(target,runs[-1],{**prior,'revision':old_revision['hash']})!='PASS':continue
                    result=deepcopy(runs[-1]);result['definition_hash']=content_hash({**gate,'revision':new_revision['hash']})
                    result['reused_from']={'work_item':identifier,'gate':gate['id'],'definition_hash':runs[-1]['definition_hash'],'stage':'integration candidate'}
                    item.setdefault('gate_results',{}).setdefault(gate['id'],[]).append(result)
    write_document(target,'work-items.yaml',document)



def remove_owned_tree(root,path):
    base=runtime_path(root)
    if path.is_symlink():path.unlink();return
    if not path.resolve().is_relative_to(base.resolve()):raise ValueError('Runtime 밖 삭제 거부')
    if not path.exists():return
    for folder,dirs,files in os.walk(path,followlinks=False):
        parent=Path(folder);parent.chmod(stat.S_IMODE(parent.stat().st_mode)|0o700)
        for name in files:
            file=parent/name
            if not file.is_symlink():file.chmod(stat.S_IMODE(file.stat().st_mode)|0o600)
    shutil.rmtree(path)
