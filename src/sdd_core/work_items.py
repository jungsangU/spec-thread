import json
from uuid import UUID

from .baseline import mapping, read_records, validate, validate_work_item

FILENAME = "work-items.yaml"


def read_plan(path):
    return mapping(json.loads(path.read_text(encoding="utf-8")), "계획")


def write_records(root, records):
    from .records import read_document, write_document
    document = read_document(root, FILENAME)
    document["work_items"] = records
    write_document(root, FILENAME, document)


def check_findings(findings):
    if not isinstance(findings, list):
        raise ValueError("findings 배열이 필요합니다")
    for finding in findings:
        finding = mapping(finding, "finding")
        assessment = finding.get("assessment")
        evidence = finding.get("evidence")
        if assessment not in ("SAFE", "UNKNOWN", "CONFLICT") or not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("영향 판정과 판단 근거가 필요합니다")
        if assessment == "UNKNOWN" and finding.get("critical") is not False:
            raise ValueError(f"핵심 UNKNOWN: {evidence}")
        if assessment == "CONFLICT":
            raise ValueError(f"CONFLICT: {evidence}")


def update(root, identifier, status, payload=None, *, related=None):
    validate(root)
    records = read_records(root, FILENAME, "work_items")
    features = read_records(root, "features.yaml", "features")
    ids = {record["id"] for record in records}
    current = next((record for record in records if record["id"] == identifier), None)
    previous = current["status"] if current else None
    allowed = {
        None: {"pending"},
        "pending": {"in_progress"},
        "in_progress": {"suspended", "completed", "failed"},
        "suspended": {"in_progress"},
    }
    if status not in allowed.get(previous, set()):
        raise ValueError(f"허용되지 않는 상태 전이: {previous} → {status}")
    if str(UUID(identifier)) != identifier or UUID(identifier).version != 7:
        raise ValueError("Work Item ID에는 표준 UUID v7이 필요합니다")

    if any(record["id"] == identifier for record in features):
        raise ValueError("Feature와 Work Item 사이에 중복 UUID가 있습니다")
    if current is None:
        from .analysis import develop_check
        develop_check(root, payload)
        related = related or []
        for previous_id in related:
            if previous_id not in ids:
                raise ValueError("이전 Work Item 참조가 없습니다")
        current = {"id": identifier, "declared_features": payload, "actual_features": []}
        current["related_work_items"] = related
        records.append(current)
    elif status == "completed":
        from .gates import require_gates
        require_gates(root, current, "complete")
        current.update(payload)
    if status == "in_progress":
        from .analysis import develop_check
        from .gates import require_gates
        if current.get("kind") != "reconciliation":
            develop_check(root, current["declared_features"] + current["actual_features"])
        require_gates(root, current, "develop")
    current["status"] = status
    validate_work_item(root, current, {record["id"] for record in features}, ids | {identifier})
    write_records(root, records)


def expand_scope(root, identifier, features, reason):
    from .analysis import develop_check
    from .baseline import nonempty, sequence
    from .gates import work_item

    validate(root)
    document, item = work_item(root, identifier, editable=True)
    features = sequence(features, "추가 Feature")
    if not features or any(not isinstance(value, str) for value in features):
        raise ValueError("추가 Feature UUID 목록이 필요합니다")
    nonempty(reason, "범위 변경 근거")
    expanded = list(dict.fromkeys(item["declared_features"] + features))
    develop_check(root, expanded)
    item.setdefault("scope_changes", []).append({
        "from": item["declared_features"], "to": expanded, "reason": reason,
    })
    item["declared_features"] = expanded
    # Stored Gate scope no longer matches; a reviewed revision is now mandatory.
    write_records(root, document["work_items"])
