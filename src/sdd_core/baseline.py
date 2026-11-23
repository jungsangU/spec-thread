import re
from pathlib import PurePosixPath
from uuid import UUID

import yaml


class BaselineLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag != "tag:yaml.org,2002:str":
                raise ValueError("Baseline YAML 키는 문자열이어야 합니다")
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ValueError(f"중복 YAML 키: {key}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def project_path(root, name):
    name = nonempty(name, "경로")
    path = PurePosixPath(name)
    if path.is_absolute() or name != path.as_posix() or name == "." or ".." in path.parts:
        raise ValueError(f"정규화된 프로젝트 상대 경로가 필요합니다: {name}")
    root = root.resolve()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"프로젝트 외부 경로입니다: {name}")
    return resolved


def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: 비어 있지 않은 문자열이 필요합니다")
    return value


def sequence(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field}: 배열이 필요합니다")
    return value


def mapping(value, field):
    if not isinstance(value, dict):
        raise ValueError(f"{field}: 매핑이 필요합니다")
    return value


def read_records(root, filename, key):
    path = project_path(root, f".specify/baseline/{filename}")
    try:
        data = mapping(yaml.load(path.read_text(encoding="utf-8"), Loader=BaselineLoader), filename)
        return [mapping(row, key) for row in sequence(data.get(key), key)]
    except (yaml.YAMLError, ValueError) as error:
        raise ValueError(f"{filename}: {error}") from error


def record_ids(records):
    ids = set()
    for record in records:
        identifier = nonempty(record.get("id"), "id")
        parsed = UUID(identifier)
        if parsed.version != 7 or str(parsed) != identifier:
            raise ValueError(f"표준 UUID v7이 필요합니다: {identifier}")
        if identifier in ids:
            raise ValueError(f"중복 UUID: {identifier}")
        ids.add(identifier)
    return ids


def require_reference(identifier, allowed, field):
    identifier = nonempty(identifier, field)
    if identifier not in allowed:
        raise ValueError(f"{field}: 참조 대상이 없습니다: {identifier}")


def source_paths(sources):
    """Read both current path records and legacy records with extra metadata."""
    return list(dict.fromkeys(
        nonempty(mapping(source, "source").get("path"), "source.path")
        for source in sequence(sources, "sources")
    ))


def scaffold(root):
    folder = project_path(root, ".specify/baseline")
    if not (root / ".specify").is_dir():
        raise ValueError("대상 프로젝트에 공식 Spec Kit를 먼저 초기화하세요")
    folder.mkdir(exist_ok=True)
    defaults = {
        "project.md": "# 프로젝트 분석\n",
        "architecture.md": "# 아키텍처\n",
        "decisions.md": "# 주요 결정\n",
        "features.yaml": "schema_version: 1\nanalysis:\n  status: not_started\n  unanalysed: []\nfeatures: []\npath_redirects: {}\n",
        "source-map.yaml": "mappings: []\n",
        "work-items.yaml": "work_items: []\n",
    }
    for name, contents in defaults.items():
        project_path(root, f".specify/baseline/{name}")
        try:
            with (folder / name).open("x", encoding="utf-8") as stream:
                stream.write(contents)
        except FileExistsError:
            continue


def validate(root, *, legacy=False):
    for filename in ("project.md", "architecture.md", "decisions.md"):
        if not project_path(root, f".specify/baseline/{filename}").is_file():
            raise ValueError(f"Baseline 파일이 없습니다: {filename}")

    data = mapping(yaml.load(project_path(root, ".specify/baseline/features.yaml").read_text(
        encoding="utf-8"), Loader=BaselineLoader), "features.yaml")
    version = data.get("schema_version")
    if version is not None and (type(version) is not int or version != 1):
        raise ValueError(f"미지원 Baseline schema_version: {version}")
    if version is None and not legacy:
        raise ValueError("Baseline schema_version이 없습니다. version-sync로 변환하세요")
    if version is not None:
        analysis = mapping(data.get("analysis"), "analysis")
        if analysis.get("status") not in ("not_started", "partial", "complete"):
            raise ValueError("프로젝트 분석 상태가 잘못되었습니다")
        sequence(analysis.get("unanalysed"), "unanalysed")
        if analysis["status"] == "complete" and analysis["unanalysed"]:
            raise ValueError("complete에는 미분석 범위가 남을 수 없습니다")
        redirects = mapping(data.get("path_redirects", {}), "path_redirects")
        for old, new in redirects.items():
            project_path(root, old)
            if not isinstance(old, str) or not old.startswith("specs/") or not isinstance(new, str) or not new.startswith("docs/sdd/archive/"):
                raise ValueError("아카이브 경로 연결이 잘못되었습니다")
            if not project_path(root, new).exists():
                raise ValueError(f"아카이브 참조를 찾을 수 없습니다: {new}")
    features = read_records(root, "features.yaml", "features")
    sources = read_records(root, "source-map.yaml", "mappings")
    work_items = read_records(root, "work-items.yaml", "work_items")
    feature_ids = record_ids(features)
    work_ids = record_ids(work_items)
    if feature_ids & work_ids:
        raise ValueError("Feature와 Work Item 사이에 중복 UUID가 있습니다")

    validate_features(root, features, legacy=legacy)
    active_ids = {feature["id"] for feature in features if feature.get("status", "active") == "active"}

    mapped_features = set()
    for source_map in sources:
        identifier = source_map.get("feature_id")
        require_reference(identifier, feature_ids, "mapping.feature_id")
        if identifier in mapped_features:
            raise ValueError(f"중복 Source Map Feature: {identifier}")
        mapped_features.add(identifier)
        for path in source_paths(source_map.get("sources")):
            if not project_path(root, path).is_file() and identifier in active_ids:
                raise ValueError(f"소스 또는 계약 파일이 없습니다: {path}")

    for item in work_items:
        validate_work_item(root, item, feature_ids, work_ids)



def validate_features(root, features, *, legacy=False):
    feature_ids = record_ids(features)
    active_ids = {row["id"] for row in features if row.get("status", "active") == "active"}
    spec_paths = set()
    for feature in features:
        nonempty(feature.get("name"), "name")
        state = feature.get("status", "active" if legacy else None)
        if state not in ("active", "retired"):
            raise ValueError("Feature status는 active 또는 retired입니다")
        name = feature.get("spec_path")
        directory = project_path(root, name)
        if directory in spec_paths:
            raise ValueError(f"중복 Feature 경로: {name}")
        spec_paths.add(directory)
        prefix = "specs/" if state == "active" else "docs/sdd/archive/"
        if not legacy and not name.startswith(prefix):
            raise ValueError(f"{state} Feature 경로는 {prefix}에 있어야 합니다")
        for filename in ("spec.md", "plan.md"):
            if not (directory / filename).is_file():
                raise ValueError(f"공식 산출물이 없습니다: {name}/{filename}")
        if state == "retired":
            retired = mapping(feature.get("retirement"), "retirement")
            nonempty(retired.get("reason"), "폐기 이유")
            nonempty(retired.get("evidence"), "폐기 결정 근거")
            for successor in sequence(retired.get("successors"), "successors"):
                require_reference(successor, feature_ids, "후속 Feature")
                if successor == feature["id"]:
                    raise ValueError("폐기 Feature는 자신을 후속으로 참조할 수 없습니다")
        for dependency in sequence(feature.get("dependencies"), "dependencies"):
            dependency = mapping(dependency, "dependency")
            require_reference(dependency.get("feature_id"), feature_ids, "dependency.feature_id")
            nonempty(dependency.get("type"), "dependency.type")
            if state == "active" and dependency["feature_id"] not in active_ids:
                raise ValueError("활성 Feature는 폐기 Feature를 현재 의존성으로 참조할 수 없습니다")


def validate_work_item(root, item, feature_ids, work_ids):
    status = nonempty(item.get("status"), "status")
    if status not in {"pending", "in_progress", "suspended", "completed", "failed"}:
        raise ValueError(f"알 수 없는 Work Item 상태: {status}")

    for field in ("declared_features", "actual_features"):
        for identifier in sequence(item.get(field), field):
            require_reference(identifier, feature_ids, field)
    for identifier in sequence(item.get("related_work_items", []), "related_work_items"):
        require_reference(identifier, work_ids, "related_work_items")

    if item.get("kind") == "reconciliation":
        reconciliation = mapping(item.get("reconciliation"), "reconciliation")
        for name in ("approval_hash", "reason"):
            nonempty(reconciliation.get(name), name)
        mapping(reconciliation.get("base"), "base")
        mapping(reconciliation.get("inputs"), "inputs")
        mapping(reconciliation.get("changes"), "changes")

    result = item.get("validation")
    if result is None and status != "completed":
        return
    result = mapping(result, "validation")
    verdict = nonempty(result.get("status"), "validation.status")
    if status == "completed" and verdict != "passed":
        raise ValueError("completed Work Item에는 passed 검증 결과가 필요합니다")
    if verdict == "passed" or "fingerprint" in result:
        value = nonempty(result.get("fingerprint"), "validation.fingerprint")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            raise ValueError("검증 Fingerprint 형식이 올바르지 않습니다")
    evidence = sequence(result.get("evidence", []), "validation.evidence")
    if verdict == "passed" and not evidence:
        raise ValueError("passed 검증 결과에는 증거 참조가 필요합니다")
    for entry in evidence:
        ref = nonempty(mapping(entry, "evidence").get("ref"), "evidence.ref")
        if "://" not in ref:
            # Prior evidence may only exist in the historical Git tree.
            project_path(root, ref.partition("#")[0])
