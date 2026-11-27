"""Atomic writes for the existing Baseline files."""
from copy import deepcopy
from .concurrency import metadata_transaction
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from .baseline import BaselineLoader, mapping, project_path

SCHEMA_VERSION = 1


class Document(dict):
    def __init__(self, value):
        super().__init__(value)
        self.original = deepcopy(value)


def merge_changes(before, ours, current, path=''):
    """CAS only changed records. Divergent edits to one record are conflicts."""
    if ours == before:
        return deepcopy(current)
    if current == before or ours == current:
        return deepcopy(ours)
    if isinstance(before, dict) and isinstance(ours, dict) and isinstance(current, dict):
        result = deepcopy(current)
        for key in set(before) | set(ours):
            if key in before and key in ours and before[key] == ours[key]:
                continue
            if key not in ours:
                if key in current and current[key] != before[key]:
                    raise ValueError(f'동시 변경 충돌: {path}/{key}')
                result.pop(key, None)
            elif key not in before:
                if key in current and current[key] != ours[key]:
                    if isinstance(ours[key],dict) and isinstance(current[key],dict):
                        result[key]=merge_changes({},ours[key],current[key],path+'/'+key);continue
                    if key in ('gates','sources','dependencies','features','mappings') and isinstance(ours[key],list) and isinstance(current[key],list):
                        result[key]=merge_changes([],ours[key],current[key],path+'/'+key);continue
                    raise ValueError(f'동시 추가 충돌: {path}/{key}')
                result[key] = deepcopy(ours[key])
            else:
                if key not in current:
                    raise ValueError(f'동시 삭제 충돌: {path}/{key}')
                result[key] = merge_changes(before[key], ours[key], current[key], path+'/'+key)
        return result
    # Baseline identity lists: records are indivisible; same-ID races are rejected.
    identities = {'work_items':'id', 'features':'id', 'mappings':'feature_id','gates':'id','sources':'path','dependencies':('feature_id','type')}
    field = identities.get(path.rsplit('/',1)[-1])
    if field and all(isinstance(v,list) for v in (before,ours,current)):
        maps=[]
        for rows in (before,ours,current):
            fields=field if isinstance(field,tuple) else (field,)
            if any(not isinstance(row,dict) or any(key not in row for key in fields) for row in rows):break
            def identity(row):return tuple(row[key] for key in fields)
            values={identity(row):row for row in rows}
            if len(values)!=len(rows):raise ValueError('중복 레코드 ID')
            maps.append(values)
        if len(maps)==3:
            base,own,latest=maps
            result=deepcopy(latest)
            for key in set(base)|set(own):
                if base.get(key)==own.get(key):continue
                if latest.get(key)!=base.get(key) and latest.get(key)!=own.get(key):
                    if path.rsplit('/',1)[-1]=='work_items' or key not in latest or key not in own:
                        raise ValueError(f'동일 레코드 동시 변경 충돌: {path}/{key}')
                    result[key]=merge_changes(base.get(key,{}),own[key],latest[key],path+'/'+str(key));continue
                if key in own:result[key]=deepcopy(own[key])
                else:result.pop(key,None)
            order=[identity(row) for row in current]+[identity(row) for row in ours if identity(row) not in latest]
            return [result[key] for key in order if key in result]
    raise ValueError(f'동시 변경 충돌: {path}')



def read_document(root, name):
    path = project_path(root, f".specify/baseline/{name}")
    return Document(mapping(yaml.load(path.read_text(encoding="utf-8"), Loader=BaselineLoader), name))


@metadata_transaction
def write_document(root, name, data):
    path = project_path(root, f".specify/baseline/{name}")
    if path != root.resolve() / ".specify/baseline" / name:
        raise ValueError("Baseline 관리 파일은 심볼릭 링크를 사용할 수 없습니다")
    current=mapping(yaml.load(path.read_text(encoding='utf-8'),Loader=BaselineLoader),name) if path.exists() else None
    if isinstance(data, Document) and current is not None:
        data = merge_changes(data.original, dict(data), current)
    if current==dict(data):return
    text = yaml.dump(dict(data),Dumper=getattr(yaml,'CSafeDumper',yaml.SafeDumper),allow_unicode=True,sort_keys=False)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(text)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


@metadata_transaction
def write_markdown(root, name, expected_hash, text):
    import hashlib
    if name not in ('project.md','architecture.md','decisions.md') or not isinstance(text,str):
        raise ValueError('공통 Markdown Baseline만 수정할 수 있습니다')
    path=project_path(root,'.specify/baseline/'+name)
    if path.is_symlink():raise ValueError('관리 Markdown 심볼릭 링크 거부')
    current=path.read_bytes()
    if hashlib.sha256(current).hexdigest()!=expected_hash:
        raise ValueError('공통 Markdown이 변경됐습니다. 현재 내용과 다시 대조하세요')
    if current!=text.encode('utf-8'):
        from .version_sync import write_file
        write_file(root,'.specify/baseline/'+name,text.encode('utf-8'))


@metadata_transaction
def update_sources(root, base, updated):
    from .baseline import read_records, require_reference, source_paths
    doc=Document(base);doc.clear();doc.update(updated)
    current=read_document(root,'source-map.yaml')
    merged=merge_changes(base,updated,current)
    features=read_records(root,'features.yaml','features')
    ids={row['id'] for row in features};active={row['id'] for row in features if row['status']=='active'}
    seen=set()
    for row in merged['mappings']:
        id=row['feature_id'];require_reference(id,ids,'mapping.feature_id')
        if id in seen:raise ValueError('중복 Source Map Feature')
        seen.add(id)
        for name in source_paths(row['sources']):
            if id in active and not project_path(root,name).is_file():raise ValueError('Source Map 파일 없음')
    write_document(root,'source-map.yaml',doc)
