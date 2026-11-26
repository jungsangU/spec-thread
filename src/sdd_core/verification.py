"""Risk profiles and reusable policy; execution stays in the existing Gate engine."""
from copy import deepcopy

from .baseline import mapping, nonempty, project_path, sequence
from .evidence import content_hash, input_files, verify_evidence
from .records import read_document, write_document
from .work_items import check_findings

FILE = 'verification.yaml'
PROFILES = ('lightweight', 'standard', 'strict')
STRICT_RISKS = ('breaking_api', 'migration', 'auth', 'security', 'transactions', 'architecture', 'broad_dependencies')
STANDARD_RISKS = ('new_feature', 'contract_changed', 'cross_feature', 'schema_change')
RISKS = STRICT_RISKS + STANDARD_RISKS
STEPS = {'discovery', 'specify', 'clarify', 'plan', 'checklist', 'tasks', 'analyze', 'implement', 'converge'}


def empty_registry():
    return {'schema_version': 1, 'status': 'unconfigured', 'reason': '', 'basis': [],
            'project': {'gates': []}, 'features': {}}


def validate_registry(root, document):
    from .gates import STAGES
    if type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        raise ValueError('verification.yaml 미지원 schema_version')
    if document.get('status') not in ('unconfigured', 'configured'):
        raise ValueError('검증 정의 상태는 unconfigured/configured입니다')
    if document['status'] == 'configured':
        nonempty(document.get('reason'), '검증 정책 근거')
        if not sequence(document.get('basis'), '검증 정책 basis'):
            raise ValueError('검증 정의의 실제 근거가 필요합니다')
    features = {f['id'] for f in read_document(root, 'features.yaml')['features']}
    scoped = mapping(document.get('features'), 'Feature 검증 정의')
    if set(scoped) - features:
        raise ValueError('검증 정의에 등록되지 않은 Feature가 있습니다')
    for owner, section in [('project', mapping(document.get('project'), 'project')), *scoped.items()]:
        seen = set()
        for gate in sequence(mapping(section, '검증 범위').get('gates'), 'gates'):
            mapping(gate, '검증 정의')
            identifier = nonempty(gate.get('id'), 'Gate ID')
            if identifier in seen:
                raise ValueError('같은 범위에 중복 Gate ID가 있습니다')
            seen.add(identifier)
            profiles = sequence(gate.get('profiles'), 'profiles')
            if not profiles or set(profiles) - set(PROFILES):
                raise ValueError('Gate 적용 프로파일이 잘못되었습니다')
            if type(gate.get('mandatory')) is not bool or type(gate.get('required')) is not bool:
                raise ValueError('mandatory/required는 boolean입니다')
            if gate['mandatory'] and not gate['required']:
                raise ValueError('모든 프로파일 필수 정책을 선택 Gate로 만들 수 없습니다')
            nonempty(gate.get('rationale'), '검증 목적')
            nonempty(gate.get('purpose', identifier), '검증 목적 식별자')
            nonempty(gate.get('evidence_requirement'), '증거 요구사항')
            if gate.get('official_step') is not None and (gate['official_step'] not in STEPS or gate.get('kind') != 'review'):
                raise ValueError('공식 절차는 서로 구분된 review Gate로 기록합니다')
            targets = gate.get('targets')
            if targets != '$scope' and (not isinstance(targets, list) or not targets or set(targets) - features):
                raise ValueError('targets는 $scope 또는 등록 Feature 배열입니다')
            if owner != 'project' and targets not in ('$scope', [owner]):
                raise ValueError('Feature Gate는 자기 Feature를 대상으로 합니다')
            if not sequence(gate.get('required_for'), 'required_for') or set(gate['required_for']) - set(STAGES):
                raise ValueError('Gate 적용 단계가 잘못되었습니다')
            paths = sequence(gate.get('paths'), 'paths')
            if not paths:
                raise ValueError('검증 입력 경로가 필요합니다')
            for path in paths:
                project_path(root, nonempty(path, '검증 입력 경로'))
            refs = sequence(gate.get('evidence'), 'evidence')
            if not refs:
                raise ValueError('검증 증거 또는 $execution이 필요합니다')
            for ref in refs:
                if ref != '$execution':
                    project_path(root, nonempty(ref, '증거').partition('#')[0])
            if gate.get('kind') == 'command':
                from .checks import check_commands
                check_commands([gate.get('command')])
            elif gate.get('kind') == 'review':
                nonempty(gate.get('method'), '검토 방법')
                if '$execution' in refs:
                    raise ValueError('의미 검토를 실행 로그로 대체할 수 없습니다')
            else:
                raise ValueError('검증 방식은 command/review입니다')
    return document


def registry(root, *, configured=True):
    document = validate_registry(root, read_document(root, FILE))
    if configured and document['status'] != 'configured':
        raise ValueError('검증 정의가 미확인입니다. 기존 검사·검토 방법을 확인해 verification.yaml을 구성하세요')
    return document


def registry_preview(root, document):
    validate_registry(root, document)
    if document['status'] != 'configured':
        raise ValueError('검증 정의 등록에는 configured와 실제 basis가 필요합니다')
    before = registry(root, configured=False)
    basis = verify_evidence(root, document['basis'])
    def entries(value):
        return {(owner, gate['id']): gate for owner, section in [('project', value['project']), *value['features'].items()]
                for gate in section['gates']}
    old, new = entries(before), entries(document)
    changed = [f'{owner}:{id}' for (owner, id), gate in old.items() if new.get((owner, id)) != gate]
    return {'previous': content_hash(before), 'document': document, 'basis': basis,
            'approval_required': bool(changed) or not new, 'approval_reasons': changed or ([] if new else ['공통 검증 정의가 없는 정책 확인'])}


def apply_registry(root, preview):
    if content_hash(registry(root, configured=False)) != preview['previous'] or verify_evidence(root, preview['document']['basis']) != preview['basis']:
        raise ValueError('검증 정의 또는 근거가 변경됐습니다')
    write_document(root, FILE, preview['document'])


def profile_record(item):
    record = item.get('verification', {}).get('revisions', [])
    if not record:
        raise ValueError('Work Item 검증 프로파일을 먼저 확정하세요')
    current = record[-1]
    if current.get('hash') != content_hash({key: value for key, value in current.items() if key != 'hash'}):
        raise ValueError('프로파일 기록 무결성 오류')
    if current['profile'] not in PROFILES:
        raise ValueError('미지원 프로파일')
    return current


def profile_preview(root, identifier, plan):
    from .gates import work_item
    registry(root)
    _, item = work_item(root, identifier, editable=True)
    reason = nonempty(plan.get('reason'), '프로파일 분류 근거')
    findings = sequence(plan.get('findings'), 'findings')
    if not findings:
        raise ValueError('프로파일 영향 근거가 필요합니다')
    check_findings(findings)
    risks = mapping(plan.get('risks'), 'risks')
    if set(risks) != set(RISKS) or any(type(value) is not bool for value in risks.values()):
        raise ValueError('모든 계약·의존성 위험 항목을 boolean으로 판단하세요')
    risks = dict(risks)
    previous = item.get('verification', {}).get('revisions', [])
    old = profile_record(item) if previous else None
    if old:
        risks = {key: risks[key] or old['risks'][key] for key in RISKS}
    scope = list(dict.fromkeys(item['declared_features'] + item['actual_features']))
    if len(scope) > 1:
        risks['cross_feature'] = True
    floor = 'strict' if any(risks[key] for key in STRICT_RISKS) else 'standard' if any(risks[key] for key in STANDARD_RISKS) else 'lightweight'
    chosen = plan.get('profile', floor)
    if chosen not in PROFILES or PROFILES.index(chosen) < PROFILES.index(floor) or (old and PROFILES.index(chosen) < PROFILES.index(old['profile'])):
        raise ValueError('계약 위험 또는 기존 프로파일보다 낮출 수 없습니다')
    conditions = mapping(plan.get('conditions', {}), '단계 적용 조건')
    if set(conditions) - {'spec_changed', 'clarify', 'discovery'} or any(type(value) is not bool for value in conditions.values()):
        raise ValueError('단계 적용 조건이 잘못되었습니다')
    required = {'plan', 'tasks', 'implement'}
    if risks['new_feature'] or risks['contract_changed'] or conditions.get('spec_changed'):
        required.add('specify')
    if risks['new_feature'] or conditions.get('discovery'):
        required.add('discovery')
    if conditions.get('clarify'):
        required.add('clarify')
    considered = mapping(plan.get('considerations', {}), '선택 검증 적용 검토')
    for name in ('checklist', 'analyze', 'converge'):
        if chosen == 'strict' or name in considered:
            decision = mapping(considered.get(name), f'{name} 적용 검토')
            nonempty(decision.get('reason'), f'{name} 적용 근거')
            if type(decision.get('required')) is not bool:
                raise ValueError('검토 결과 required는 boolean입니다')
            if decision['required']:
                required.add(name)
    extra = sequence(plan.get('additional_steps', []), 'additional_steps')
    if set(extra) - STEPS:
        raise ValueError('알 수 없는 필수 절차입니다')
    required.update(extra)
    if old:
        required.update(old['required_steps'])
    uncertain = plan.get('uncertain', False)
    if type(uncertain) is not bool:
        raise ValueError('uncertain은 boolean입니다')
    strict_approval = chosen == 'strict' and (old is None or old['profile'] != 'strict' or any(risks[key] and not old['risks'][key] for key in STRICT_RISKS))
    return {'work_item': identifier, 'previous': content_hash(previous), 'item_hash': content_hash(item), 'profile': chosen, 'risks': risks,
            'reason': reason, 'scope': scope, 'conditions': conditions, 'considerations': considered,
            'required_steps': sorted(required), 'findings': findings, 'basis': verify_evidence(root, plan.get('basis')),
            'approval_required': strict_approval or uncertain,
            'approval_reasons': (['Strict 최초 분류·상향 또는 새 고위험'] if strict_approval else []) + (['중요 판단 불확실성'] if uncertain else [])}


def apply_profile(root, identifier, preview, *, delegated=False):
    from .gates import work_item
    document, item = work_item(root, identifier, editable=True)
    state = item.get('verification', {'revisions': [], 'steps': {}})
    if content_hash(item) != preview['item_hash'] or content_hash(state['revisions']) != preview['previous'] or verify_evidence(root, list(preview['basis'])) != preview['basis']:
        raise ValueError('프로파일 입력 또는 이력이 변경됐습니다')
    item['verification'] = state
    record = deepcopy(preview)
    record['approval_mode'] = ('office_ceo' if delegated else
                               'explicit_user' if preview['approval_required'] else 'request_scope')
    record['preview_hash'] = content_hash(preview)
    record['hash'] = content_hash(record)
    state['revisions'].append(record)
    write_document(root, 'work-items.yaml', document)


def templates(root, item):
    record = {'profile': 'strict', 'scope': item['declared_features'] + item['actual_features']} if item.get('kind') == 'reconciliation' else profile_record(item)
    scope = list(dict.fromkeys(item['declared_features'] + item['actual_features']))
    if set(record['scope']) != set(scope):
        raise ValueError('범위 변경 후 프로파일을 다시 평가하세요')
    document = registry(root)
    active = {row['id'] for row in read_document(root, 'features.yaml')['features'] if row['status'] == 'active'}
    selected = []
    for owner, section in [('project', document['project']), *[(id, document['features'][id]) for id in scope if id in active and id in document['features']]]:
        for template in section['gates']:
            if not template['mandatory'] and record['profile'] not in template['profiles']:
                continue
            gate = {key: deepcopy(value) for key, value in template.items() if key not in ('profiles', 'mandatory')}
            if gate['targets'] == '$scope':
                gate['targets'] = scope if owner == 'project' else [owner]
            if set(gate['targets']) - set(scope):
                raise ValueError('선택 검증 정의의 대상이 현재 범위와 다릅니다')
            if '$execution' in gate['evidence']:
                import re
                if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', gate['id']):
                    raise ValueError('자동 로그 Gate ID가 경로로 안전하지 않습니다')
                gate['evidence'] = [f'docs/sdd/evidence/{item["id"]}/{gate["id"]}.log' if ref == '$execution' else ref for ref in gate['evidence']]
                gate['capture_log'] = True
            selected.append((owner, gate))
    return selected


def compose(root, item, additional):
    gates, sources = {}, {}
    for owner, gate in [*templates(root, item), *[('work_item', gate) for gate in additional]]:
        id = gate['id']
        if id in gates and gates[id] != gate:
            raise ValueError(f'같은 ID의 검증 정의 충돌: {id}')
        gates[id] = gate
        sources.setdefault(id, []).append(owner)
    return list(gates.values()), sources


def enforce(root, item, gates):
    actual = {gate['id']: gate for gate in gates}
    for owner, expected in templates(root, item):
        if expected['required'] and actual.get(expected['id']) != expected:
            raise ValueError(f'현재 정책의 필수 Gate 누락/변경: {owner}:{expected["id"]}')


def steps_required(root, item):
    if item.get('kind') == 'reconciliation':
        return
    record = profile_record(item)
    saved = item.get('verification', {}).get('steps', {})
    required = set(record['required_steps'])
    for gate in item.get('gate_revisions', [{}])[-1].get('gates', []):
        if gate.get('required') and gate.get('official_step'):
            required.add(gate['official_step'])
    for name in required:
        history = saved.get(name, [])
        if not history or history[-1].get('status') not in ('done', 'reused'):
            raise ValueError(f'프로파일 필수 절차 미완료: {name}')
        evidence = verify_evidence(root, list(history[-1]['evidence']))
        if name in ('analyze', 'converge', 'checklist'):
            result = history[-1]
            if evidence != result['evidence'] or input_files(root, list(result.get('inputs', {}))) != result.get('inputs'):
                raise ValueError(f'필수 공식 검토 입력/증거가 변경됐습니다: {name}')


def record_step(root, identifier, name, plan):
    from .gates import work_item
    if name not in STEPS:
        raise ValueError('공식 절차 이름이 잘못되었습니다')
    document, item = work_item(root, identifier, editable=True)
    profile_record(item)
    status = plan.get('status')
    if status not in ('done', 'reused'):
        raise ValueError('필수 절차를 생략/추정 완료할 수 없습니다')
    nonempty(plan.get('conclusion'), '절차 수행/재사용 결론')
    if name == 'analyze' and not item.get('verification', {}).get('steps', {}).get('tasks'):
        raise ValueError('analyze는 tasks 이후에 수행합니다')
    if name == 'converge' and not item.get('verification', {}).get('steps', {}).get('implement'):
        raise ValueError('converge는 implement 이후에 수행합니다')
    if name in ('tasks', 'implement', 'analyze', 'converge'):
        features = {row['id']: row for row in read_document(root, 'features.yaml')['features']}
        for id in item['declared_features']:
            if not project_path(root, features[id]['spec_path'] + '/tasks.md').is_file():
                raise ValueError('공식 tasks.md 전제를 충족하세요')
    from datetime import datetime, timezone
    entry = {'status': status, 'step': name, 'conclusion': plan['conclusion'],
             'recorded_at': datetime.now(timezone.utc).isoformat(),
             'evidence': verify_evidence(root, plan.get('evidence'))}
    if plan.get('paths') is not None or name in ('analyze', 'converge', 'checklist'):
        entry['inputs'] = input_files(root, plan.get('paths'))
    if status == 'reused' and name in ('analyze', 'converge', 'checklist'):
        source = mapping(plan.get('source'), '공식 결과 원본 참조')
        if source.get('step') != name or type(source.get('index')) is not int or source['index'] < 0:
            raise ValueError('서로 다른 목적의 공식 절차를 대체할 수 없습니다')
        _, original = work_item(root, source.get('work_item'))
        prior = original.get('verification', {}).get('steps', {}).get(name, [])
        if source['index'] >= len(prior):
            raise ValueError('기록된 공식 결과 원본이 없습니다')
        previous = prior[source['index']]
        if previous.get('inputs') != entry.get('inputs') or previous.get('evidence') != entry['evidence']:
            raise ValueError('입력 또는 증거가 다른 공식 검증 결과는 재사용할 수 없습니다')
        entry['source'] = source
    duration = plan.get('elapsed_seconds')
    if duration is not None:
        import math
        if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
            raise ValueError('절차 소요 시간은 실제 측정한 음수 아닌 값입니다')
        entry['elapsed_seconds'] = duration
    item['verification'].setdefault('steps', {}).setdefault(name, []).append(entry)
    write_document(root, 'work-items.yaml', document)


def auto_gate_allowed(item, gates):
    old = item.get('gate_revisions', [])
    if not old:
        return True
    new = {gate['id']: gate for gate in gates}
    for gate in old[-1]['gates']:
        if gate['required'] and new.get(gate['id']) != gate:
            return False
    return True


def validate_work_record(root, item, feature_ids, work_ids):
    state = mapping(item['verification'], 'Work Item verification')
    revisions = sequence(state.get('revisions'), '프로파일 이력')
    previous = None
    for index, record in enumerate(revisions):
        record = mapping(record, '프로파일')
        if record.get('hash') != content_hash({key: value for key, value in record.items() if key != 'hash'}):
            raise ValueError('프로파일 기록 무결성 오류')
        if record.get('previous') != content_hash(revisions[:index]):
            raise ValueError('프로파일 이전 이력 연결 오류')
        if record.get('profile') not in PROFILES or set(sequence(record.get('scope'), '프로파일 범위')) - feature_ids:
            raise ValueError('프로파일 종류/범위 오류')
        risks = mapping(record.get('risks'), '위험 분류')
        if set(risks) != set(RISKS) or any(type(value) is not bool for value in risks.values()):
            raise ValueError('프로파일 위험 구조 오류')
        steps = set(sequence(record.get('required_steps'), '필수 절차'))
        if steps - STEPS or not {'plan', 'tasks', 'implement'}.issubset(steps):
            raise ValueError('공통 필수 절차 누락')
        if previous and (PROFILES.index(record['profile']) < PROFILES.index(previous['profile']) or
                         any(previous['risks'][key] and not risks[key] for key in RISKS) or
                         not set(previous['required_steps']).issubset(steps)):
            raise ValueError('프로파일 이력에서 위험·필수 절차를 낮출 수 없습니다')
        if record.get('approval_required') and record.get('approval_mode') not in ('explicit_user', 'office_ceo'):
            raise ValueError('구체적 승인 경로 기록이 없습니다')
        previous = record
    for step, history in mapping(state.get('steps'), '절차 이력').items():
        if step not in STEPS:
            raise ValueError('알 수 없는 절차 이력')
        for entry in sequence(history, '절차 결과'):
            entry = mapping(entry, '절차 결과')
            if entry.get('step') != step or entry.get('status') not in ('done', 'reused'):
                raise ValueError('절차 목적·상태 불일치')
            nonempty(entry.get('conclusion'), '절차 결론')
            if not mapping(entry.get('evidence'), '절차 증거'):
                raise ValueError('절차 증거 없음')
            for ref in entry['evidence']:
                project_path(root, ref.partition('#')[0])
            source = entry.get('source')
            if source and (not isinstance(source, dict) or source.get('work_item') not in work_ids or source.get('step') != step):
                raise ValueError('절차 원본 참조 불일치')
