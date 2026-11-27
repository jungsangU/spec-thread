from .concurrency import metadata_transaction
from copy import deepcopy

from .baseline import mapping, nonempty, sequence, validate
from .checks import CheckFailure, run_checks, check_commands
from .evidence import content_hash, current_result, input_files, planned_inputs, verify_evidence
from .records import read_document, write_document

STAGES = ("develop", "verify", "complete")


def work_item(root, identifier, *, editable=False):
    document = read_document(root, "work-items.yaml")
    for item in document["work_items"]:
        if item["id"] == identifier:
            if editable and item["status"] not in ("pending", "in_progress", "suspended"):
                raise ValueError("종료된 Work Item은 변경할 수 없습니다")
            return document, item
    raise ValueError(f"Work Item이 없습니다: {identifier}")


def definitions(root, plan, scope, *, allow_missing_evidence=False):
    gates = sequence(plan.get("gates"), "gates")
    if not gates or not any(mapping(gate, "gate").get("required") is True for gate in gates):
        raise ValueError("적용 필수 Gate가 필요합니다")
    ids = set()
    for gate in gates:
        mapping(gate, "gate")
        identifier = nonempty(gate.get("id"), "Gate ID")
        if identifier in ids:
            raise ValueError("Gate ID가 중복되었습니다")
        ids.add(identifier)
        nonempty(gate.get("rationale"), "Gate 적용 근거")
        if gate.get("official_step") is not None:
            from .verification import STEPS
            if gate["official_step"] not in STEPS or gate.get("kind") != "review":
                raise ValueError("공식 절차 Gate는 구분된 review 방법으로 기록하세요")
        if type(gate.get("required")) is not bool:
            raise ValueError("Gate required는 boolean입니다")
        targets = sequence(gate.get("targets"), "targets")
        if not targets or set(targets) - set(scope):
            raise ValueError("Gate 대상은 선언된 Feature 범위여야 합니다")
        stages = sequence(gate.get("required_for"), "required_for")
        if not stages or set(stages) - set(STAGES):
            raise ValueError("required_for는 develop/verify/complete입니다")
        planned_inputs(root, gate.get("paths"))
        nonempty(gate.get("evidence_requirement"), "증거 요구사항")
        if gate.get("kind") == "command":
            check_commands([gate.get("command")])
            outputs = sequence(gate.get("evidence"), "evidence")
            if not outputs:
                raise ValueError("실행 결과 증거 경로를 지정하세요")
            from .baseline import project_path
            for name in outputs:
                project_path(root, nonempty(name, "evidence"))
        elif gate.get("kind") == "review":
            nonempty(gate.get("method"), "검토 방법")
            if allow_missing_evidence:
                planned_inputs(root, [ref.partition("#")[0] for ref in sequence(gate.get("evidence"), "evidence")])
            else:
                verify_evidence(root, gate.get("evidence"))
        else:
            raise ValueError("Gate kind는 command 또는 review입니다")
    covered = {target for gate in gates if gate["required"] for target in gate["targets"]}
    if set(scope) - covered:
        raise ValueError("일부 Feature에 필수 Gate가 없습니다")
    return gates


def prepare_gate_plan(root, identifier, plan, *, compose_policy=False):
    validate(root)
    _, item = work_item(root, identifier, editable=True)
    scope = list(dict.fromkeys(item["declared_features"] + item["actual_features"]))
    from .verification import compose, enforce, auto_gate_allowed
    policy_sources = {}
    if compose_policy:
        plan = deepcopy(plan)
        plan['gates'], policy_sources = compose(root, item, plan.get('gates', []))
    gates = definitions(root, plan, scope, allow_missing_evidence=True)
    enforce(root, item, gates)
    reason = nonempty(plan.get("reason"), "Gate 집합 결정/변경 근거")
    inputs = {}
    for gate in gates:
        inputs.update(planned_inputs(root, gate["paths"]))
    basis = verify_evidence(root, plan.get("basis"))
    preview = {
        "work_item": identifier, "previous": content_hash(item.get("gate_revisions", [])),
        "scope": scope, "gates": gates, "reason": reason, "basis": basis, "inputs": inputs,
        "policy_sources": policy_sources,
        "approval_required": not auto_gate_allowed(item, gates),
    }
    return preview


@metadata_transaction
def register_gates(root, identifier, preview):
    document, item = work_item(root, identifier, editable=True)
    if content_hash(item.get("gate_revisions", [])) != preview["previous"]:
        raise ValueError("Gate 집합이 변경됐습니다")
    from .verification import enforce
    enforce(root, item, preview['gates'])
    old = item.get('gate_revisions', [])
    previous = old[-1] if old else None
    revision = deepcopy(preview)
    revision["hash"] = content_hash(preview)
    item.setdefault("gate_revisions", []).append(revision)
    old_basis_valid = False
    if previous:
        try:
            old_basis_valid = verify_evidence(root, list(previous['basis'])) == previous['basis']
        except (OSError, ValueError):
            pass
    if previous and old_basis_valid:
        old_defs = {gate['id']: gate for gate in previous['gates']}
        for gate in revision['gates']:
            history = item.get('gate_results', {}).get(gate['id'], [])
            prior = old_defs.get(gate['id'])
            if prior == gate and history and current_result(root, history[-1], {**prior, 'revision': previous['hash']}) == 'PASS':
                result = deepcopy(history[-1])
                result['reused_from'] = {'work_item': identifier, 'gate': gate['id'], 'run_index': len(history) - 1, 'definition_hash': result['definition_hash']}
                result['definition_hash'] = content_hash({**gate, 'revision': revision['hash']})
                history.append(result)
    write_document(root, "work-items.yaml", document)


def latest_revision(root, item, *, allow_missing_evidence=False):
    revisions = item.get("gate_revisions", [])
    if not revisions:
        raise ValueError("개발/검증 진입 전에 필수 Gate 집합을 확정하세요")
    revision = revisions[-1]
    saved = {key: value for key, value in revision.items() if key != "hash"}
    if content_hash(saved) != revision.get("hash"):
        raise ValueError("Gate 집합 기록 무결성 오류")
    if verify_evidence(root, list(revision["basis"])) != revision["basis"]:
        raise ValueError("Gate 적용 근거가 변경됐습니다. 새 집합을 검토하세요")
    scope = list(dict.fromkeys(item["declared_features"] + item["actual_features"]))
    if set(scope) != set(revision["scope"]):
        raise ValueError("Work Item 범위와 Gate 집합 범위가 다릅니다")
    definitions(root, revision, scope, allow_missing_evidence=True)
    from .verification import enforce
    enforce(root, item, revision['gates'])
    return revision


def gate_status(root, item, stage):
    if stage not in STAGES:
        raise ValueError("단계는 develop/verify/complete입니다")
    revision = latest_revision(root, item)
    if stage == 'complete':
        from .verification import steps_required
        steps_required(root, item)
    results = []
    for gate in revision["gates"]:
        if not gate["required"] or (stage != "complete" and not any(
            STAGES.index(required) <= STAGES.index(stage) for required in gate["required_for"]
        )):
            continue
        applicable = {**gate, "revision": revision["hash"]}
        runs = item.get("gate_results", {}).get(gate["id"], [])
        results.append({"id": gate["id"], "status": current_result(root, runs[-1] if runs else None, applicable)})
    return results


def require_gates(root, item, stage):
    statuses = gate_status(root, item, stage)
    blocked = [row for row in statuses if row["status"] != "PASS"]
    if blocked:
        raise ValueError(f"필수 Gate 차단: {blocked}")
    return statuses


def execute_gate(root, identifier, gate_id, review=None, *, force=False):
    validate(root)
    document, item = work_item(root, identifier, editable=True)
    revision = latest_revision(root, item)
    gate = next((gate for gate in revision["gates"] if gate["id"] == gate_id), None)
    if gate is None:
        raise ValueError("확정 집합에 없는 Gate입니다")
    # Development prerequisites must pass before verification-only gates run.
    if "develop" not in gate["required_for"]:
        require_gates(root, item, "develop")
    if "verify" not in gate["required_for"] and "develop" not in gate["required_for"]:
        require_gates(root, item, "verify")
    history = item.get('gate_results', {}).get(gate_id, [])
    bound = {**gate, 'revision': revision['hash']}
    if not force and review is None and history and current_result(root, history[-1], bound) == 'PASS':
        return {**history[-1], 'action': 'reuse', 'reused_from': {'work_item': identifier, 'gate': gate_id, 'run_index': len(history) - 1}}
    # Equal explicit purpose + execution scope/input/evidence can share one actual result.
    def objective(value):
        return {key: value.get(key) for key in ('kind', 'command', 'method', 'targets', 'paths', 'evidence', 'evidence_requirement', 'official_step')} | {'purpose': value.get('purpose', value['id'])}
    if not force and review is None:
        for other in revision['gates']:
            runs = item.get('gate_results', {}).get(other['id'], [])
            if other['id'] != gate_id and objective(other) == objective(gate) and runs and current_result(root, runs[-1], {**other, 'revision': revision['hash']}) == 'PASS':
                result = deepcopy(runs[-1])
                result.update(definition_hash=content_hash(bound), reused_from={'work_item': identifier, 'gate': other['id'], 'run_index': len(runs) - 1, 'definition_hash': result['definition_hash']})
                item.setdefault('gate_results', {}).setdefault(gate_id, []).append(result)
                write_document(root, 'work-items.yaml', document)
                return {**result, 'action': 'reuse'}
    history_hash = content_hash(item)
    management_hash = content_hash({k:v for k,v in document.items() if k != "work_items"})
    before = input_files(root, gate["paths"])
    from .evidence import input_modes
    before_modes=input_modes(root,gate["paths"])
    bound = {**gate, "revision": revision["hash"]}
    result = {"status": "UNKNOWN", "definition_hash": content_hash(bound), "inputs": before,"input_modes":before_modes}
    from .workspaces import execution_context
    context=execution_context(root)
    if context is not None:result["execution_context"]=context
    try:
        if gate["kind"] == "command":
            if review is not None:
                raise ValueError("command Gate의 결과를 외부 PASS로 대체할 수 없습니다")
            runs = run_checks(root, [gate["command"]])
            result["execution"] = runs[0]
        else:
            review = mapping(review, "review")
            nonempty(review.get("reviewer"), "reviewer")
            nonempty(review.get("conclusion"), "검토 결론")
            if review.get("status") not in ("PASS", "FAIL", "UNKNOWN", "NOT_RUN"):
                raise ValueError("검토 결과 상태가 잘못되었습니다")
            result["review"] = review
            result["status"] = review["status"]
        result["evidence"] = verify_evidence(root, gate["evidence"])
        if gate["kind"] == "command":
            result["status"] = "PASS"
        if input_files(root, gate["paths"]) != before:
            result["status"] = "STALE"
    except (OSError, ValueError) as error:
        result["status"] = "FAIL"
        result["error"] = str(error)
        if isinstance(error, CheckFailure):
            result["execution"] = error.result

    if gate.get('capture_log'):
        from .version_sync import write_file, json_bytes
        expected = f'docs/sdd/evidence/{identifier}/{gate_id}.log'
        if gate_id not in ('', '.', '..') and expected in gate['evidence'] and len(gate_id) <= 100 and '/' not in gate_id and '\\' not in gate_id:
            write_file(root, expected, json_bytes(result.get('execution', {'error': result.get('error')})))
            try:
                result['evidence'] = verify_evidence(root, gate['evidence'])
                if input_files(root, gate['paths']) != before:
                    result['status'] = 'STALE'
                elif result.get('execution', {}).get('exit_code') == 0:
                    result['status'] = 'PASS'
                    result.pop('error', None)
            except (OSError, ValueError) as error:
                result.update(status='FAIL', error=str(error))
        else:
            raise ValueError('자동 실행 로그는 Core가 정한 경로에만 기록합니다')
    from .concurrency import project_lock
    with project_lock(root):
        current_document, current_item = work_item(root, identifier, editable=True)
        if content_hash({k:v for k,v in current_document.items() if k != "work_items"}) != management_hash:
            raise ValueError("검증 중 관리 구조가 변경됐습니다")
        if content_hash(current_item) != history_hash:
            raise ValueError('검증 중 동일 Work Item/Gate 기록이 변경됐습니다')
        current_revision = latest_revision(root, current_item)
        if current_revision['hash'] != revision['hash']:
            raise ValueError('검증 정책이 변경됐습니다')
        try:
            changed=input_files(root,gate['paths'])!=before or input_modes(root,gate['paths'])!=before_modes or execution_context(root)!=context
        except (OSError,ValueError):changed=True
        if changed:result['status']='STALE'
        if result['status'] == 'PASS' and verify_evidence(root, gate['evidence']) != result.get('evidence'):
            result['status'] = 'STALE'
        from .workspaces import retain_evidence
        retain_evidence(root,identifier,result)
        current_item.setdefault('gate_results', {}).setdefault(gate_id, []).append(result)
        write_document(root, 'work-items.yaml', current_document)
    return result
