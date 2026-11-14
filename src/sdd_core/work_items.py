import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

import yaml

from .baseline import mapping, project_path, read_records, validate, validate_work_item

FILENAME = "work-items.yaml"


def read_plan(path):
    return mapping(json.loads(path.read_text(encoding="utf-8")), "계획")


def write_records(root, records):
    destination = project_path(root, f".specify/baseline/{FILENAME}")
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            yaml.safe_dump({"work_items": records}, stream, allow_unicode=True, sort_keys=False)
            stream.close()
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


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


def update(root, identifier, status, payload=None):
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
        current = {"id": identifier, "declared_features": payload, "actual_features": []}
        records.append(current)
    elif status == "completed":
        current.update(payload)
    current["status"] = status
    validate_work_item(root, current, {record["id"] for record in features}, ids | {identifier})
    write_records(root, records)
