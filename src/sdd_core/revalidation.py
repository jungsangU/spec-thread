"""Approved selective revalidation; no watcher, scheduler, or separate state store."""
from copy import deepcopy
import hashlib

from .analysis import develop_check
from .baseline import project_path, validate
from .evidence import content_hash, current_result, planned_inputs
from .gates import (STAGES, execute_gate, latest_revision, prepare_gate_plan,
                    register_gates, work_item)
from .records import read_document, write_document

IGNORED = {'.git', '.venv', 'venv', 'node_modules', '.agents', '.claude', '__pycache__'}


def prepare(root, identifier, stage='complete'):
    if stage not in STAGES:
        raise ValueError('검증 단계 오류')
    _, item = work_item(root, identifier, editable=True)
    revision = latest_revision(root, item, allow_missing_evidence=True)
    selected = [g for g in revision['gates'] if g['required'] and (stage == 'complete' or any(
        STAGES.index(x) <= STAGES.index(stage) for x in g['required_for']))]
    index = None
    renames = {}
    ambiguous = {}
    watched = {'.specify/baseline/work-items.yaml', '.specify/baseline/source-map.yaml',
               '.specify/baseline/features.yaml', '.specify/spec-thread.json'}
    watched.update(ref.partition('#')[0] for ref in revision['basis'])
    for gate in selected:
        runs = item.get('gate_results', {}).get(gate['id'], [])
        result = runs[-1] if runs else {}
        for field in ('inputs', 'evidence'):
            for ref, digest in result.get(field, {}).items():
                name = ref.partition('#')[0]
                watched.add(name)
                if project_path(root, name).is_file():
                    continue
                if index is None:
                    index = {}
                    for path in root.rglob('*'):
                        relative = path.relative_to(root)
                        if IGNORED.intersection(relative.parts) or path.is_symlink() or not path.is_file():
                            continue
                        key = hashlib.sha256(path.read_bytes()).hexdigest()
                        index.setdefault(key, []).append(relative.as_posix())
                candidates = sorted(index.get(digest, []))
                if len(candidates) == 1:
                    renames[name] = candidates[0]
                    watched.add(candidates[0])
                else:
                    ambiguous[name] = candidates
    revised = deepcopy(revision['gates'])
    for gate in revised:
        for field in ('paths', 'evidence'):
            gate[field] = [renames.get(ref.partition('#')[0], ref.partition('#')[0]) +
                           ('#' + ref.partition('#')[2] if '#' in ref else '') for ref in gate[field]]
        if gate['kind'] == 'command':
            for arg in gate['command']:
                if any(old in arg and arg != old for old in renames):
                    ambiguous['command:' + gate['id']] = ['경로가 명령 문자열 안에 포함됨: 명시적 Gate 개정 필요']
            gate['command'] = [renames.get(arg, arg) for arg in gate['command']]
    actions = []
    for gate in selected:
        runs = item.get('gate_results', {}).get(gate['id'], [])
        status = current_result(root, runs[-1] if runs else None, {**gate, 'revision': revision['hash']})
        actions.append({'gate': gate['id'], 'status': status, 'action': 'reuse' if status == 'PASS' else 'run'})
        watched.update(gate['paths'])
        watched.update(ref.partition('#')[0] for ref in gate['evidence'])
    # Bind candidate discovery too: a duplicate appearing after approval invalidates it.
    return {'work_item': identifier, 'stage': stage, 'previous': revision['hash'],
            'renames': renames, 'ambiguous': ambiguous, 'gates': revised, 'actions': actions,
            'inputs': planned_inputs(root, sorted(watched))}


def refresh(root, identifier, preview):
    if preview['ambiguous']:
        raise ValueError(f"삭제·모호한 이름 변경을 수동으로 해소하세요: {preview['ambiguous']}")
    _, original = work_item(root, identifier, editable=True)
    previous = deepcopy(latest_revision(root, original, allow_missing_evidence=True))
    if preview['renames']:
        sources = read_document(root, 'source-map.yaml')
        active = {f['id'] for f in read_document(root, 'features.yaml')['features'] if f['status'] == 'active'}
        for row in sources['mappings']:
            if row['feature_id'] in active:
                for source in row['sources']:
                    source['path'] = preview['renames'].get(source['path'], source['path'])
        write_document(root, 'source-map.yaml', sources)
        validate(root)
        new_plan = {'reason': '사용자가 승인한 동일 내용 파일 위치 변경과 선택적 재검증',
                    'basis': list(previous['basis']), 'gates': preview['gates']}
        revision = prepare_gate_plan(root, identifier, new_plan)
        register_gates(root, identifier, revision)
        # Carry only byte-identical definitions with a currently valid latest PASS.
        document, item = work_item(root, identifier, editable=True)
        latest = latest_revision(root, item)
        old_defs = {gate['id']: gate for gate in previous['gates']}
        for gate in latest['gates']:
            old = old_defs.get(gate['id'])
            runs = item.get('gate_results', {}).get(gate['id'], [])
            if old == gate and runs and current_result(root, runs[-1], {**old, 'revision': previous['hash']}) == 'PASS':
                copied = deepcopy(runs[-1])
                copied['reused_from'] = {'work_item': identifier, 'gate': gate['id'],
                                         'run_index': len(runs) - 1, 'definition_hash': copied['definition_hash']}
                copied['definition_hash'] = content_hash({**gate, 'revision': latest['hash']})
                runs.append(copied)
        write_document(root, 'work-items.yaml', document)
    validate(root)
    _, item = work_item(root, identifier, editable=True)
    if item.get('kind') != 'reconciliation':
        develop_check(root, item['declared_features'] + item['actual_features'])
    results = []
    # Existing stage prerequisites and execution remain the single gate engine.
    gates = latest_revision(root, item)['gates']
    order = sorted(preview['actions'], key=lambda a: min(STAGES.index(s) for s in next(
        g for g in gates if g['id'] == a['gate'])['required_for']))
    for action in order:
        _, item = work_item(root, identifier, editable=True)
        gate = next(g for g in latest_revision(root, item)['gates'] if g['id'] == action['gate'])
        runs = item.get('gate_results', {}).get(gate['id'], [])
        status = current_result(root, runs[-1] if runs else None,
                                {**gate, 'revision': latest_revision(root, item)['hash']})
        if status == 'PASS':
            results.append({'gate': gate['id'], 'status': 'PASS', 'action': 'reuse'})
            continue
        if gate['kind'] == 'review':
            results.append({'gate': gate['id'], 'status': status, 'action': 'review_required'})
            break
        result = execute_gate(root, identifier, gate['id'])
        results.append({'gate': gate['id'], 'status': result['status'], 'action': 'run'})
        if result['status'] != 'PASS':
            break
    return {'work_item': identifier, 'results': results,
            'status': 'PASS' if len(results) == len(order) and all(r['status'] == 'PASS' for r in results) else 'BLOCKED'}
