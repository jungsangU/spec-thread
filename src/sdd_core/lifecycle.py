from .concurrency import metadata_transaction
import json
import posixpath
import re
from copy import deepcopy
from urllib.parse import unquote

import yaml

from .baseline import mapping, nonempty, project_path, sequence, validate
from .evidence import content_hash, input_files
from .records import read_document, write_document

LINK = re.compile(r'(!?\[[^\]]*\]\()([^\s)]+)(\))')


def markdown_links(text, old_file, new_file, redirects):
    def replace(match):
        ref = match[2]
        path, separator, anchor = ref.partition("#")
        if not path or "://" in path or path.startswith("//"):
            return match[0]
        absolute = path.startswith("/")
        target = posixpath.normpath(path.lstrip("/") if absolute else
                                    posixpath.join(posixpath.dirname(old_file), unquote(path)))
        for old, new in redirects.items():
            if target == old or target.startswith(old + "/"):
                target = new + target[len(old):]
                break
        location = "/" + target if absolute else posixpath.relpath(target, posixpath.dirname(new_file) or ".")
        return match[1] + location + (separator + anchor if separator else "") + match[3]
    return LINK.sub(replace, text)


def prepare_retirement(root, identifier, plan):
    validate(root)
    document = read_document(root, "features.yaml")
    features = {row["id"]: row for row in document["features"]}
    if identifier not in features or features[identifier]["status"] != "active":
        raise ValueError("활성 Feature만 폐기할 수 있습니다")
    feature = features[identifier]
    old = feature["spec_path"]
    destination = f"docs/sdd/archive/{identifier}"
    if project_path(root, destination).exists():
        raise ValueError("아카이브 대상이 이미 존재합니다")
    reason = nonempty(plan.get("reason"), "폐기 이유")
    evidence = nonempty(plan.get("evidence"), "결정 근거 파일")
    from .evidence import verify_evidence
    decision_evidence = verify_evidence(root, [evidence])
    successors = sequence(plan.get("successors"), "successors")
    if len(set(successors)) != len(successors):
        raise ValueError("후속 Feature 중복")
    for successor in successors:
        if successor not in features or features[successor]["status"] != "active" or successor == identifier:
            raise ValueError("후속 Feature는 다른 활성 Feature여야 합니다")
    # An in-flight request must be stopped before its feature is retired.
    work = read_document(root, "work-items.yaml")
    for item in work["work_items"]:
        if item["status"] not in ("completed", "failed") and identifier in (
            item["declared_features"] + item["actual_features"]
        ):
            raise ValueError("폐기 대상에 미종료 Work Item이 있습니다")
    updated = deepcopy(document)
    rows = {row["id"]: row for row in updated["features"]}
    updates = mapping(plan.get("dependency_updates"), "dependency_updates")
    affected = {
        row["id"] for row in features.values() if row["status"] == "active"
        and row["id"] != identifier
        and any(dep["feature_id"] == identifier for dep in row["dependencies"])
    }
    if not affected.issubset(updates):
        raise ValueError("폐기 Feature의 활성 소비자 의존성을 재평가하세요")
    for target, dependencies in updates.items():
        if target not in rows or rows[target]["status"] != "active" or target == identifier:
            raise ValueError("의존성 재평가 대상이 잘못되었습니다")
        rows[target]["dependencies"] = sequence(dependencies, "dependencies")
        for dependency in dependencies:
            mapping(dependency, "dependency")
            dep = dependency.get("feature_id")
            if dep not in rows or rows[dep]["status"] != "active" or dep == identifier:
                raise ValueError("현재 의존관계는 활성 Feature를 참조해야 합니다")
            nonempty(dependency.get("type"), "dependency.type")
    rows[identifier]["status"] = "retired"
    rows[identifier]["spec_path"] = destination
    rows[identifier]["retirement"] = {"reason": reason, "evidence": evidence, "successors": successors}
    updated.setdefault("path_redirects", {})[old] = destination
    # Changing the graph invalidates discovery records through its input fingerprints.
    redirects = {old: destination}
    writes = {}
    moves = {}
    for path in project_path(root, old).rglob("*"):
        if path.is_symlink():
            raise ValueError("아카이브 산출물의 심볼릭 링크를 먼저 확인하세요")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            moves[name] = destination + name[len(old):]
    ignored = {".git", ".venv", "node_modules", ".agents", ".claude"}
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if ignored.intersection(relative.parts) or path.is_symlink():
            continue
        name = relative.as_posix()
        text = path.read_text(encoding="utf-8")
        target = moves.get(name, name)
        revised = markdown_links(text, name, target, redirects)
        # Root-relative plain evidence refs embedded in documentation.
        revised = revised.replace(old + "/", destination + "/")
        if revised != text:
            writes[target] = revised.encode("utf-8")
    sources = read_document(root, "source-map.yaml")
    original_sources = deepcopy(sources)
    for source_map in sources["mappings"]:
        if rows[source_map["feature_id"]]["status"] != "active":
            continue
        for source in source_map["sources"]:
            name = source["path"]
            if name == old or name.startswith(old + "/"):
                source["path"] = destination + name[len(old):]
    if sources != original_sources:
        writes[".specify/baseline/source-map.yaml"] = yaml.safe_dump(
            sources, allow_unicode=True, sort_keys=False,
        ).encode("utf-8")
    # Preserve completed Work Items byte-for-byte; redirects resolve historical refs.
    selector = ".specify/feature.json"
    selector_data = project_path(root, selector)
    if selector_data.is_file():
        data = json.loads(selector_data.read_text(encoding="utf-8"))
        if data.get("feature_directory") == old:
            data.pop("feature_directory")
            writes[selector] = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    # Archive record follows the moved decision evidence path.
    retired_evidence = rows[identifier]["retirement"]["evidence"]
    if retired_evidence.startswith(old + "/"):
        rows[identifier]["retirement"]["evidence"] = destination + retired_evidence[len(old):]
    names = set(moves) | {name for name in writes if name not in moves.values()}
    names |= {".specify/baseline/" + name for name in (
        "features.yaml", "source-map.yaml", "work-items.yaml", "project.md", "decisions.md", "architecture.md"
    )}
    if selector_data.is_file():
        names.add(selector)
    names.add(evidence.partition("#")[0])
    for target in set(updates) | set(successors):
        names.update(f"{features[target]['spec_path']}/{filename}" for filename in ("spec.md", "plan.md"))
    inputs = input_files(root, sorted(names))
    preview = {"feature": identifier, "from": old, "to": destination, "reason": reason,
               "successors": successors, "dependency_updates": updates, "decision_evidence": decision_evidence, "moves": moves,
               "writes": {name: content_hash(list(data)) for name, data in writes.items()},
               "inputs": inputs, "features_hash": content_hash(updated)}
    return preview, updated, writes


@metadata_transaction
def retire(root, preview, updated, writes):
    try:
        source = project_path(root, preview["from"])
        destination = project_path(root, preview["to"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        for name, contents in writes.items():
            path = project_path(root, name)
            path.write_bytes(contents)
        write_document(root, "features.yaml", updated)
        validate(root)
        check_archive_links(root, preview["to"])
    except (OSError, ValueError) as error:
        raise ValueError(f"아카이브 적용 실패. 사용자 Git 원복 후 처음부터 재검토하세요: {error}") from error


def check_archive_links(root, folder):
    for path in project_path(root, folder).rglob("*.md"):
        for match in LINK.finditer(path.read_text(encoding="utf-8")):
            ref = match[2].partition("#")[0]
            if not ref or "://" in ref or ref.startswith("//"):
                continue
            name = posixpath.normpath(ref.lstrip("/") if ref.startswith("/") else
                                     posixpath.join(path.parent.relative_to(root).as_posix(), unquote(ref)))
            if not project_path(root, name).exists():
                raise ValueError(f"아카이브 문서 링크 누락: {path.name}: {ref}")
