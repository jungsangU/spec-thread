import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from .baseline import BaselineLoader, mapping, project_path, validate
from .checks import run_checks
from .work_items import check_findings

BASELINE = ".specify/baseline/"
# Git reads these as separate records even when the YAML text overlaps.
STRUCTURED = {
    BASELINE + "features.yaml": ("features", "id"),
    BASELINE + "source-map.yaml": ("mappings", "feature_id"),
    BASELINE + "work-items.yaml": ("work_items", "id"),
}


def git(root, *args, data=None, env=None):
    result = subprocess.run(
        ["git", "-C", str(root), *args], input=data, capture_output=True, env=env,
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise ValueError(f"Git {args[0]} 실패: {detail}")
    return result.stdout


def ref(root, name):
    return git(root, "rev-parse", "--verify", name).decode().strip()


def snapshot(root, paths, ancestor, index):
    if not isinstance(paths, list) or not paths:
        raise ValueError("선택할 경로가 필요합니다")
    for path in paths:
        project_path(root, path)
    env = dict(os.environ, GIT_INDEX_FILE=str(index))
    git(root, "read-tree", ancestor, env=env)
    git(root, "--literal-pathspecs", "add", "-A", "--", *paths, env=env)
    return git(root, "write-tree", env=env).decode().strip()


def records(root, tree, path, key, identity):
    listing = git(root, "ls-tree", tree, "--", path)
    if not listing:
        return {}
    contents = git(root, "show", f"{tree}:{path}")
    try:
        document = mapping(yaml.load(contents, Loader=BaselineLoader), path)
        result = {}
        for row in document[key]:
            identifier = row[identity]
            if identifier in result:
                raise ValueError(f"중복 레코드: {identifier}")
            result[identifier] = row
        return result
    except (yaml.YAMLError, KeyError, TypeError) as error:
        raise ValueError(f"Baseline 읽기 실패: {path}") from error


def merge_records(base, ours, theirs, location):
    result = []
    for identifier in dict.fromkeys([*ours, *theirs, *base]):
        value = merge_value(
            base.get(identifier), ours.get(identifier), theirs.get(identifier),
            f"{location}/{identifier}",
        )
        if value is not None:
            result.append(value)
    return result


def merge_value(base, ours, theirs, location):
    if ours == theirs or theirs == base:
        return ours
    if ours == base:
        return theirs
    if all(isinstance(value, dict) for value in (base, ours, theirs)):
        result = {}
        for key in dict.fromkeys([*ours, *theirs, *base]):
            value = merge_value(base.get(key), ours.get(key), theirs.get(key), f"{location}/{key}")
            if value is not None:
                result[key] = value
        return result
    for field, keys in (
        ("dependencies", ("feature_id", "type")),
        ("sources", ("path", "symbol")),
    ):
        if location.endswith("/" + field) and all(
            isinstance(value, list) for value in (base, ours, theirs)
        ):
            indexed = [{tuple(row[key] for key in keys): row for row in rows}
                       for rows in (base, ours, theirs)]
            return merge_records(*indexed, location)
    raise ValueError(f"Baseline 통합 충돌: {location}")


def apply_source(temp, ancestor, source, ours):
    diff = git(
        temp, "diff", "--binary", "--full-index", "--no-ext-diff",
        ancestor, source, "--", ".", *[f":(exclude){path}" for path in STRUCTURED],
    )
    if diff:
        git(temp, "apply", "--index", "--3way", data=diff)
    for path, (key, identity) in STRUCTURED.items():
        if not git(temp, "diff", "--name-only", ancestor, source, "--", path):
            continue
        base, current, incoming = [
            records(temp, tree, path, key, identity) for tree in (ancestor, ours, source)
        ]
        merged = merge_records(base, current, incoming, path)
        destination = temp / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink() or not destination.resolve().is_relative_to(temp):
            raise ValueError(f"Baseline 경로가 임시 작업 공간을 벗어났습니다: {path}")
        destination.write_text(
            yaml.safe_dump({key: merged}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        git(temp, "add", "--", path)
    return git(temp, "write-tree").decode().strip()


def require_inactive_target(root, branch):
    worktrees = git(root, "worktree", "list", "--porcelain", "-z").split(b"\0")
    if b"branch " + branch.encode() in worktrees:
        raise ValueError("대상 브랜치를 사용 중인 작업 공간에서 먼저 전환하세요")


def integrate(root, plan, preview=False):
    if not preview:
        check_findings(plan.get("findings"))
    if plan.get("safe_worktrees") is not True:
        raise ValueError("전체 Worktree의 안전 상태를 확인해야 합니다")
    branch = plan.get("target")
    if not isinstance(branch, str) or not branch.startswith("refs/heads/"):
        raise ValueError("대상은 refs/heads/로 시작하는 로컬 브랜치여야 합니다")
    git(root, "check-ref-format", branch)
    base = ref(root, branch)
    require_inactive_target(root, branch)
    selections = plan.get("sources")
    if not isinstance(selections, list) or not selections:
        raise ValueError("선택한 Worktree가 필요합니다")
    message = plan.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("커밋 메시지가 필요합니다")
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    with TemporaryDirectory(prefix="sdd-integration-") as folder:
        workspace = Path(folder).resolve()
        temp = workspace / "candidate"
        git(root, "worktree", "add", "--detach", str(temp), base)
        try:
            candidate = ref(temp, "HEAD^{tree}")
            for index, selection in enumerate(selections):
                selection = mapping(selection, "source")
                source_root = Path(selection["worktree"]).resolve(strict=True)
                if git(source_root, "rev-parse", "--path-format=absolute", "--git-common-dir") != common:
                    raise ValueError(f"같은 저장소의 Worktree가 아닙니다: {source_root}")
                if Path(git(source_root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != source_root:
                    raise ValueError(f"Worktree 루트가 필요합니다: {source_root}")
                head = ref(source_root, "HEAD")
                ancestor = git(root, "merge-base", base, head).decode().strip()
                paths = selection["paths"]
                if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
                    raise ValueError("선택 경로는 문자열 배열이어야 합니다")
                if BASELINE + "work-items.yaml" not in paths:
                    raise ValueError("선택 경로에 work-items.yaml이 필요합니다")
                source = snapshot(source_root, paths, ancestor, workspace / f"index-{index}")
                items = records(root, source, BASELINE + "work-items.yaml", "work_items", "id")
                selected_ids = selection.get("work_items")
                if not isinstance(selected_ids, list) or not selected_ids or any(
                    items.get(item, {}).get("status") != "completed" for item in selected_ids
                ):
                    raise ValueError(f"선택 Worktree에 완료 기록이 없습니다: {source_root}")
                previous = records(root, ancestor, BASELINE + "work-items.yaml", "work_items", "id")
                unexpected = {
                    item for item in items.keys() | previous.keys()
                    if items.get(item) != previous.get(item)
                } - set(selected_ids)
                if unexpected:
                    raise ValueError(f"선택되지 않은 Work Item 변경: {', '.join(sorted(unexpected))}")
                candidate = apply_source(temp, ancestor, source, candidate)

            validate(temp)
            completed = records(temp, candidate, BASELINE + "work-items.yaml", "work_items", "id")
            for selection in selections:
                ids = selection.get("work_items")
                if not isinstance(ids, list) or not ids or any(
                    completed.get(item, {}).get("status") != "completed" for item in ids
                ):
                    raise ValueError("선택된 Work Item이 통합 트리에서 completed 상태여야 합니다")
            if preview:
                return {
                    "base": base,
                    "tree": candidate,
                    "diff": git(temp, "diff", "--no-ext-diff", base, candidate).decode(errors="replace"),
                }
            if plan.get("reviewed_base") != base or plan.get("reviewed_tree") != candidate:
                raise ValueError("미리보기의 기준 또는 통합 트리가 변경됐습니다")
            run_checks(temp, plan.get("checks"))
            if (
                git(temp, "diff", "--name-only")
                or git(temp, "ls-files", "--others", "--exclude-standard")
                or git(temp, "write-tree").decode().strip() != candidate
            ):
                raise ValueError("검증 도중 통합 트리가 변경됐습니다")
            if candidate == ref(root, f"{base}^{{tree}}"):
                raise ValueError("반영할 변경이 없습니다")
            commit = git(root, "commit-tree", candidate, "-p", base, "-m", message).decode().strip()
        finally:
            git(root, "worktree", "remove", "--force", str(temp))
        require_inactive_target(root, branch)
        git(root, "update-ref", branch, commit, base)
        return commit
