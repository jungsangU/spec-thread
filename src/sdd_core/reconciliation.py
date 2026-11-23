"""User-approved external reconciliation using existing Work Items and Gates."""
import subprocess
from copy import deepcopy

from .baseline import mapping, nonempty, project_path, sequence, validate
from .checks import check_commands
from .evidence import content_hash, planned_inputs, verify_evidence
from .gates import prepare_gate_plan, register_gates
from .records import read_document, write_document
from .work_items import check_findings

BASELINE = '.specify/baseline/'
DOCUMENTS = {BASELINE + name for name in ('project.md', 'architecture.md', 'decisions.md', 'source-map.yaml')}


def comparison_base(root, config):
    config = mapping(config, 'base')
    if config.get('kind') == 'git':
        revision = nonempty(config.get('revision'), 'base.revision')
        result = subprocess.run(['git', 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}'],
                                cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise ValueError('비교 revision을 commit으로 확인할 수 없습니다')
        return {'kind': 'git', 'revision': revision, 'commit': result.stdout.strip()}
    if config.get('kind') == 'files':
        return {'kind': 'files', 'evidence': verify_evidence(root, config.get('refs'))}
    raise ValueError('base.kind는 git 또는 files입니다')


def prepare(root, plan):
    document = read_document(root, 'features.yaml')
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise ValueError("미지원 Baseline schema_version입니다. 쓰기 전에 동기화 계약을 확인하세요")
    from .baseline import record_ids
    record_ids(document["features"])
    features = sequence(plan.get('features'), 'features')
    active = {row['id'] for row in document['features'] if row['status'] == 'active'}
    if not features or any(not isinstance(x, str) for x in features) or set(features) - active:
        raise ValueError('정합화 대상은 등록된 활성 Feature여야 합니다')
    reason = nonempty(plan.get('reason'), 'reason')
    findings = sequence(plan.get('findings'), 'findings')
    if not findings:
        raise ValueError('정합화 영향 판단 근거가 필요합니다')
    check_findings(findings)
    base = comparison_base(root, plan.get('base'))
    basis = verify_evidence(root, plan.get('basis'))
    paths = sequence(plan.get('paths'), 'paths')
    if not paths:
        raise ValueError('관찰한 코드·계약·증거 입력을 지정하세요')
    changes = sequence(plan.get('changes'), 'changes')
    if not changes:
        raise ValueError('승인할 정합화 변경이 없습니다')
    writes = {}
    for change in changes:
        change = mapping(change, 'change')
        name = nonempty(change.get('path'), 'change.path')
        target = project_path(root, name)
        if name not in DOCUMENTS and not (name.startswith('specs/') and target.suffix == '.md'):
            raise ValueError('Sync는 승인된 공식 Markdown·기존 Baseline 문서/Source Map만 갱신합니다')
        if target != root.resolve() / name:
            raise ValueError('정합화 관리 파일은 심볼릭 링크일 수 없습니다')
        if name in writes or not isinstance(change.get('content'), str):
            raise ValueError('변경 경로 중복 또는 잘못된 content입니다')
        writes[name] = change['content']
    verification = deepcopy(mapping(plan.get('verification'), 'verification'))
    nonempty(verification.get('reason'), 'verification.reason')
    verify_evidence(root, verification.get('basis'))
    gates = sequence(verification.get('gates'), 'verification.gates')
    covered = set()
    ids = set()
    for gate in gates:
        gate = mapping(gate, 'gate')
        identifier = nonempty(gate.get('id'), 'Gate ID')
        if identifier in ids:
            raise ValueError('Gate ID 중복')
        ids.add(identifier)
        nonempty(gate.get('rationale'), 'rationale')
        nonempty(gate.get('evidence_requirement'), 'evidence_requirement')
        targets = sequence(gate.get('targets'), 'targets')
        if not targets or set(targets) - set(features) or type(gate.get('required')) is not bool:
            raise ValueError('정합화 Gate 범위가 잘못되었습니다')
        stages = sequence(gate.get('required_for'), 'required_for')
        if not stages or set(stages) - {'develop', 'verify', 'complete'}:
            raise ValueError('required_for가 잘못되었습니다')
        if gate['required']:
            covered.update(targets)
        planned_inputs(root, gate.get('paths'))
        if gate.get('kind') == 'command':
            check_commands([gate.get('command')])
            refs = sequence(gate.get('evidence'), 'evidence')
            if not refs:
                raise ValueError('실행 증거가 필요합니다')
            for ref in refs:
                project_path(root, ref)
        elif gate.get('kind') == 'review':
            nonempty(gate.get('method'), 'method')
            verify_evidence(root, gate.get('evidence'))
        else:
            raise ValueError('Gate kind 오류')
    if set(features) - covered:
        raise ValueError('모든 정합화 대상에 필수 Gate가 필요합니다')
    watched = set(paths) | set(writes) | {ref.partition("#")[0] for ref in basis}
    watched.update(BASELINE + x for x in ('project.md', 'architecture.md', 'decisions.md',
                                         'features.yaml', 'source-map.yaml', 'work-items.yaml'))
    watched.add('.specify/spec-thread.json')
    watched.update(['.specify/feature.json', '.specify/memory/constitution.md'])
    for row in document['features']:
        if row['id'] in features:
            for path in project_path(root, row['spec_path']).rglob('*'):
                if path.is_file():
                    watched.add(path.relative_to(root).as_posix())
    from .version_sync import skill_marker, skill_path, ACTIVE, read_marker, PROJECT
    agent = read_marker(root, PROJECT)['agent']
    watched.add(skill_marker(agent))
    watched.update(skill_path(agent, x) for x in ACTIVE)
    for gate in gates:
        watched.update(gate['paths'])
    watched.update(ref.partition('#')[0] for ref in verification['basis'])
    preview = {'base': base, 'features': features, 'reason': reason, 'findings': findings,
               'basis': basis, 'writes': writes, 'verification': verification,
               'inputs': planned_inputs(root, sorted(watched))}
    return preview


def apply(root, preview, identifier):
    # The caller has recomputed the preview and checked its approval hash.
    work = read_document(root, 'work-items.yaml')
    if identifier in {x['id'] for x in work['work_items']} | {
        x['id'] for x in read_document(root, 'features.yaml')['features']
    }:
        raise ValueError('정합화 Work Item UUID 중복')
    item = {'id': identifier, 'kind': 'reconciliation', 'status': 'in_progress',
            'declared_features': preview['features'], 'actual_features': [], 'related_work_items': [],
            'reconciliation': {'approval_hash': content_hash(preview), 'base': preview['base'],
                               'inputs': preview['inputs'], 'reason': preview['reason'],
                               'findings': preview['findings'],
                               'changes': {p: content_hash(v) for p, v in preview['writes'].items()}}}
    work['work_items'].append(item)
    write_document(root, 'work-items.yaml', work)
    try:
        for name, content in preview['writes'].items():
            target = project_path(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
        validate(root)
        gate_plan = prepare_gate_plan(root, identifier, preview['verification'])
        register_gates(root, identifier, gate_plan)
    except (OSError, ValueError, KeyError, TypeError) as error:
        current = read_document(root, 'work-items.yaml')
        record = next(x for x in current['work_items'] if x['id'] == identifier)
        record['status'] = 'failed'
        record['reconciliation']['error'] = str(error)
        write_document(root, 'work-items.yaml', current)
        raise ValueError(f'정합화 적용 실패 ({identifier}). 부분 변경을 사용자 Git으로 원복한 뒤 새 승인으로 재시도: {error}') from error
    return {'work_item': identifier, 'status': 'in_progress', 'changed_paths': list(preview['writes']),
            'next': 'gate-run 또는 gate-refresh 후 complete로 검증·완료'}
