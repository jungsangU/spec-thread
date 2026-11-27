import hashlib
import json
from urllib.parse import unquote

from .baseline import nonempty, project_path, sequence


def content_hash(value):
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()



def planned_inputs(root, paths):
    paths = sequence(paths, "paths")
    if not paths:
        raise ValueError("검증 입력 paths가 필요합니다")
    result = {}
    for name in paths:
        name = nonempty(name, "path")
        path = project_path(root, name)
        if path.exists() and not path.is_file():
            raise ValueError(f"검증 입력은 파일이어야 합니다: {name}")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return dict(sorted(result.items()))


def input_files(root, paths):
    paths = sequence(paths, "paths")
    if not paths:
        raise ValueError("검증 입력 paths가 필요합니다")
    result = {}
    for name in paths:
        name = nonempty(name, "path")
        path = project_path(root, name)
        if not path.is_file():
            raise ValueError(f"검증 입력 파일이 없습니다: {name}")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(result.items()))


def resolve_evidence(root, name):
    from .records import read_document
    name = unquote(name)
    path = project_path(root, name)
    if path.exists():
        return path
    document_path = project_path(root, ".specify/baseline/features.yaml")
    if document_path.is_file():
        for old, new in read_document(root, "features.yaml").get("path_redirects", {}).items():
            if name == old or name.startswith(old + "/"):
                return project_path(root, new + name[len(old):])
    return path


def verify_evidence(root, refs):
    refs = sequence(refs, "evidence")
    if not refs:
        raise ValueError("실제 증거 참조가 필요합니다")
    results = {}
    for ref in refs:
        ref = nonempty(ref, "evidence ref")
        if "://" in ref:
            raise ValueError("Gate 증거는 프로젝트 안에 보존한 파일을 참조하세요")
        name, _, anchor = ref.partition("#")
        path = resolve_evidence(root, name)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"증거 파일이 없거나 비어 있습니다: {ref}")
        if anchor.startswith("L") and anchor[1:].isdigit():
            if not 1 <= int(anchor[1:]) <= len(path.read_text(encoding="utf-8").splitlines()):
                raise ValueError(f"증거 줄 범위가 유효하지 않습니다: {ref}")
        results[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
    return results


def current_result(root, result, definition):
    if not result:
        return "NOT_RUN"
    if result.get("status") != "PASS":
        return result.get("status", "UNKNOWN")
    try:
        from .workspaces import execution_context
        context=execution_context(root)
        if context is not None and result.get("execution_context")!=context:return "STALE"
        if "input_modes" in result and input_modes(root,list(result["inputs"]))!=result["input_modes"]:return "STALE"
        if set(result.get("inputs", {})) != set(definition.get("paths", [])):
            return "UNKNOWN"
        if set(result.get("evidence", {})) != set(definition.get("evidence", [])):
            return "UNKNOWN"
        if definition.get("kind") == "command":
            execution = result.get("execution", {})
            if execution.get("command") != definition["command"] or execution.get("exit_code") != 0:
                return "UNKNOWN"
        elif definition.get("kind") == "review":
            review = result.get("review", {})
            if review.get("status") != "PASS" or not review.get("reviewer") or not review.get("conclusion"):
                return "UNKNOWN"
        if result.get("definition_hash") != content_hash(definition):
            return "STALE"
        if result.get("inputs") != input_files(root, list(result.get("inputs", {}))):
            return "STALE"
        if result.get("evidence") != verify_evidence(root, list(result.get("evidence", {}))):
            return "STALE"
    except (OSError, ValueError):
        return "STALE"
    return "PASS"



def input_modes(root,paths):
    import stat
    return {name:stat.S_IMODE(project_path(root,name).stat().st_mode) for name in paths}
