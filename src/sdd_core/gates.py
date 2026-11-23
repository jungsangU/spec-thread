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


def prepare_gate_plan(root, identifier, plan):
    validate(root)
    _, item = work_item(root, identifier, editable=True)
    scope = list(dict.fromkeys(item["declared_features"] + item["actual_features"]))
    gates = definitions(root, plan, scope)
    reason = nonempty(plan.get("reason"), "Gate 집합 결정/변경 근거")
    inputs = {}
    for gate in gates:
        inputs.update(planned_inputs(root, gate["paths"]))
    basis = verify_evidence(root, plan.get("basis"))
    preview = {
        "work_item": identifier, "previous": content_hash(item.get("gate_revisions", [])),
        "scope": scope, "gates": gates, "reason": reason, "basis": basis, "inputs": inputs,
    }
    return preview


def register_gates(root, identifier, preview):
    document, item = work_item(root, identifier, editable=True)
    if content_hash(item.get("gate_revisions", [])) != preview["previous"]:
        raise ValueError("Gate 집합이 변경됐습니다")
    revision = deepcopy(preview)
    revision["hash"] = content_hash(preview)
    item.setdefault("gate_revisions", []).append(revision)
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
    definitions(root, revision, scope, allow_missing_evidence=allow_missing_evidence)
    return revision


def gate_status(root, item, stage):
    if stage not in STAGES:
        raise ValueError("단계는 develop/verify/complete입니다")
    revision = latest_revision(root, item)
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


def execute_gate(root, identifier, gate_id, review=None):
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
    history_hash = content_hash(document)
    before = input_files(root, gate["paths"])
    bound = {**gate, "revision": revision["hash"]}
    result = {"status": "UNKNOWN", "definition_hash": content_hash(bound), "inputs": before}
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
    if content_hash(read_document(root, "work-items.yaml")) != history_hash:
        raise ValueError("검증 중 Work Item/Gate 기록이 변경됐습니다. 결과를 다시 검토하세요")
    item.setdefault("gate_results", {}).setdefault(gate_id, []).append(result)
    write_document(root, "work-items.yaml", document)
    return result
