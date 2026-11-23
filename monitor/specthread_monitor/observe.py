"""Read the selected worktree and project records without applying Core operations."""
from itertools import islice
import os
import re
import selectors
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import unquote

from sdd_core import __version__ as CORE_VERSION
from sdd_core.baseline import project_path, validate
from sdd_core.evidence import current_result
from sdd_core.gates import STAGES, latest_revision
from sdd_core.records import SCHEMA_VERSION, read_document
from sdd_core.version_sync import (ACTIVE, FOLDERS, PROJECT, RETIRED, RUNNER,
                                   digest, installed_agent, read_marker, require_skills, skill_marker, skill_path)
from yaml import YAMLError

BASELINE = ".specify/baseline/"
DOCUMENT_LIMIT = 2 * 1024 * 1024
EVIDENCE_LIMIT = 8 * 1024 * 1024
STATE_FILES = ("features.yaml", "source-map.yaml", "work-items.yaml")
ERRORS = (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, YAMLError)
ARTIFACTS = ("spec.md", "plan.md", "tasks.md", "research.md", "data-model.md", "quickstart.md")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_file(path, limit):
    if path.exists() and (not path.is_file() or path.stat().st_size > limit):
        raise ValueError("지원하는 파일 유형 또는 크기 범위를 벗어났습니다")
    return path


def git(root, *args, limit=256 * 1024, configs=()):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
               "-c", "core.hooksPath=/dev/null", "-C", str(root)]
    for config in configs:
        command.extend(("-c", config))
    command.extend(args)
    deadline = time.monotonic() + 3
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env) as proc:
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                data = bytearray()
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise ValueError("Git 읽기 시간 한도를 초과했습니다")
                    chunk = os.read(proc.stdout.fileno(), 16384)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > limit:
                        raise ValueError("Git 출력 크기 한도를 초과했습니다")
            if proc.wait(timeout=max(0.01, deadline - time.monotonic())):
                raise ValueError("Git 정보를 읽을 수 없습니다")
            return data.decode("utf-8", errors="replace")
        finally:
            if proc.poll() is None:
                proc.kill()


def filter_overrides(root):
    keys = git(root, "config", "--null", "--name-only", "--list").split("\0")
    drivers = {key.rsplit(".", 1)[0] for key in keys if re.fullmatch(
        r"filter\.[^=\r\n]+\.(process|clean|smudge|required)", key
    )}
    return tuple(f"{driver}.{setting}={value}" for driver in sorted(drivers)
                 for setting, value in (("process", ""), ("clean", ""), ("smudge", ""), ("required", "false")))


def changes(root):
    if git(root, "rev-parse", "--show-prefix").strip():
        raise ValueError("Git Worktree 루트를 지정하세요")
    try:
        branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD").strip()
    except ValueError:
        branch = git(root, "rev-parse", "--short", "HEAD").strip()
    entries = git(root, "status", "--porcelain=v1", "-z", "--no-renames",
                  "--untracked-files=all", "--ignore-submodules=all", configs=filter_overrides(root)).split("\0")
    files = [{"status": row[:2], "path": row[3:]} for row in entries if row]
    return {"branch": branch, "files": files[:250], "total": len(files)}


def diff(root, name, staged):
    project_path(root, name)
    if not any(row["path"] == name for row in changes(root)["files"]):
        raise ValueError("표시된 변경 경로를 선택하세요")
    args = ["--cached"] if staged else []
    return git(root, "--literal-pathspecs", "diff", "--no-ext-diff", "--no-textconv",
               "--no-renames", "--ignore-submodules=all", *args, "--", name, configs=filter_overrides(root))


def artifact(root, name, changed):
    path = project_path(root, name)
    try:
        info = path.stat() if path.is_file() else None
    except OSError:
        info = None
    return {"path": name, "present": info is not None, "changed": name in changed,
            "modified": datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat() if info else None}


def discover_artifacts(root, directories, changed, *, budget=400):
    paths = {BASELINE + name for name in ("project.md", "architecture.md", "decisions.md",
                                         "features.yaml", "source-map.yaml", "work-items.yaml")}
    paths.add(".specify/memory/constitution.md")
    for directory in directories[:100]:
        paths.update(f"{directory}/{name}" for name in ARTIFACTS[:3])
        for name in ARTIFACTS[3:]:
            relative = f"{directory}/{name}"
            if project_path(root, relative).is_file():
                paths.add(relative)
        for folder in ("contracts", "checklists"):
            candidate = project_path(root, f"{directory}/{folder}")
            if candidate.is_dir():
                for entry in islice(candidate.iterdir(), 40):
                    if not entry.is_symlink() and entry.is_file():
                        paths.add(f"{directory}/{folder}/{entry.name}")
    return [artifact(root, name, changed) for name in sorted(paths)[:budget]]


def limited_evidence(root, document, revision):
    paths = set()
    for gate in revision.get("gates", []):
        paths.update(gate.get("paths", []))
        paths.update(unquote(ref.partition("#")[0]) for ref in gate.get("evidence", []))
    paths.update(unquote(ref.partition("#")[0]) for ref in revision.get("basis", {}))
    if len(paths) > 100:
        raise ValueError("Gate 경로 개수 한도 초과")
    remaining = EVIDENCE_LIMIT
    for name in paths:
        mapped = name
        if not project_path(root, name).exists():
            for old, new in document.get("path_redirects", {}).items():
                if name == old or name.startswith(old + "/"):
                    mapped = new + name[len(old):]
                    break
        path = safe_file(project_path(root, mapped), remaining)
        if path.is_file():
            remaining -= path.stat().st_size


def gates(root, document, item, budget):
    revisions = item.get("gate_revisions", [])
    results = item.get("gate_results", {})
    if not revisions:
        return [], "필수 Gate 집합 기록 없음"
    historical = item["status"] in ("completed", "failed")
    revision = revisions[-1]
    issue = None
    if not historical:
        try:
            if budget["remaining"] <= 0:
                raise ValueError("스냅샷 Gate 읽기 한도")
            budget["remaining"] -= 1
            limited_evidence(root, document, revision)
            revision = latest_revision(root, item)
        except ERRORS:
            issue = "Gate 정의 또는 증거의 현재 유효성을 확인할 수 없습니다"
    rows = []
    for definition in revision.get("gates", [])[:100]:
        identifier = definition["id"]
        runs = results.get(identifier, [])
        saved = runs[-1] if runs else None
        stages = definition["required_for"]
        required = definition["required"]
        status = saved.get("status", "UNKNOWN") if saved else "NOT_RUN"
        current = None if historical else (
            "UNKNOWN" if issue else current_result(root, saved, {**definition, "revision": revision["hash"]})
        )
        if not isinstance(identifier, str) or type(required) is not bool:
            raise ValueError("잘못된 Gate 기록")
        rows.append({"id": identifier, "required": required,
                     "recorded": status if isinstance(status, str) else "UNKNOWN",
                     "current": current if isinstance(current, str) else ("UNKNOWN" if current is not None else None),
                     "historical": historical, "runs": len(runs),
                     "evidence": [ref for ref in definition.get("evidence", []) if isinstance(ref, str)],
                     "stages": [stage for index, stage in enumerate(STAGES)
                                if required and (stage == "complete" or any(s in STAGES[:index + 1] for s in stages))]})
    return rows, issue


def task_summary(root, directory):
    path = safe_file(project_path(root, f"{directory}/tasks.md"), DOCUMENT_LIMIT)
    if not path.is_file():
        return None
    markers = re.findall(r"^\s*[-*+]\s+\[([ xX])\]\s", path.read_text(encoding="utf-8"), re.M)
    return {"done": sum(value.lower() == "x" for value in markers), "total": len(markers)}


def file_signature(path):
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return info.st_ino, info.st_size, info.st_mtime_ns


def project_records(root):
    paths = [safe_file(project_path(root, BASELINE + name), DOCUMENT_LIMIT) for name in STATE_FILES]
    signatures = [file_signature(path) for path in paths]
    document = read_document(root, "features.yaml")
    if type(document.get("schema_version")) is not int or document["schema_version"] != SCHEMA_VERSION:
        version = document.get("schema_version")
        return {"state": "unsupported", "schema": version if type(version) in (int, str) else None}
    validate(root)
    feature_rows = document["features"]
    work_rows = read_document(root, "work-items.yaml")["work_items"]
    features = []
    for row in feature_rows[:100]:
        feature = {key: row[key] for key in ("id", "name", "status", "spec_path", "dependencies")}
        feature["dependencies"] = [{key: edge[key] for key in ("feature_id", "type")} for edge in row["dependencies"]]
        discovery = row.get("discovery", {})
        verdict = discovery.get("verdict") if isinstance(discovery, dict) else None
        feature["discovery"] = verdict if verdict in ("READY", "CONDITIONAL", "BLOCKED") else None
        try:
            feature["tasks"] = task_summary(root, row["spec_path"])
        except ERRORS:
            feature["tasks"] = None
        features.append(feature)
    items = []
    budget = {"remaining": 16}
    for row in work_rows[-100:][::-1]:
        try:
            gates_rows, issue = gates(root, document, row, budget)
        except ERRORS:
            gates_rows, issue = [], "Gate 기록 형식을 읽을 수 없습니다"
        items.append({**{key: row.get(key) for key in (
            "id", "status", "declared_features", "actual_features", "related_work_items",
        )}, "gates": gates_rows, "gate_issue": issue})
    if signatures != [file_signature(path) for path in paths]:
        raise ValueError("읽는 중 Baseline이 변경되었습니다")
    return {"state": "available", "schema": SCHEMA_VERSION, "analysis": document["analysis"]["status"],
            "features": features, "items": items, "feature_count": len(feature_rows), "item_count": len(work_rows)}


def installation(root):
    paths = [PROJECT, RUNNER]
    for agent in FOLDERS:
        paths.append(skill_marker(agent))
        paths.extend(skill_path(agent, name) for name in (*ACTIVE, RETIRED))
    for name in paths:
        safe_file(project_path(root, name), DOCUMENT_LIMIT)
    record = read_marker(root, PROJECT)
    if record is None:
        return None
    quality = record.get("quality", {})
    if not isinstance(quality, dict):
        raise ValueError("잘못된 품질 기록")
    restricted = quality.get("restricted_features")
    global_blocked = quality.get("global_blocked")
    quality_available = (isinstance(global_blocked, bool) and isinstance(restricted, list)
                         and all(isinstance(name, str) for name in restricted))
    agent = record.get("agent")
    version = record.get("core_version")
    try:
        if version != CORE_VERSION or not quality_available:
            raise ValueError("설치 기록을 대조할 수 없습니다")
        require_skills(root, installed_agent(root, None, record))
        if digest(project_path(root, RUNNER).read_bytes()) != record.get("runner_hash"):
            raise ValueError("runner 해시가 다릅니다")
        installation_status = "MATCH"
    except ERRORS:
        installation_status = "UNVERIFIED"
    return {"agent": agent if isinstance(agent, str) else None,
            "core_version": version if isinstance(version, str) else None,
            "record_integrity": installation_status,
            "quality_available": quality_available, "global_blocked": global_blocked if quality_available else None,
            "restricted_features": restricted[:100] if quality_available else []}


def next_actions(baseline, installed):
    actions = []
    if baseline["state"] == "unsupported":
        actions.append({"text": "기존 Core 버전·스키마 확인", "ref": BASELINE + "features.yaml"})
    if installed and (installed["global_blocked"] or installed["restricted_features"]):
        actions.append({"text": "저장된 품질 제한의 근거 확인", "ref": PROJECT})
    for item in baseline.get("items", []):
        if item["status"] in ("failed", "completed"):
            continue
        if item["status"] == "suspended":
            actions.append({"text": "보류한 작업의 재개 여부 검토", "ref": item["id"]})
        elif item["gate_issue"] or any(gate["required"] and gate["current"] != "PASS" for gate in item["gates"]):
            actions.append({"text": "필수 Gate 정의와 결과 검토", "ref": item["id"]})
    for feature in baseline.get("features", []):
        tasks = feature["tasks"]
        if feature["status"] == "active" and tasks and tasks["done"] < tasks["total"]:
            actions.append({"text": "미완료 공식 태스크 확인", "ref": f"{feature['spec_path']}/tasks.md"})
    return actions[:20]


def snapshot(root):
    alerts = {}
    try:
        git_state = changes(root)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        git_state = None
        alerts["git"] = "Git 상태를 읽을 수 없습니다"
    try:
        baseline = project_records(root)
    except FileNotFoundError:
        baseline = {"state": "missing"}
    except ERRORS:
        baseline = {"state": "unavailable"}
        alerts["baseline"] = "Baseline 구조 또는 참조를 읽을 수 없습니다"
    try:
        installed = installation(root)
    except ERRORS:
        installed = None
        alerts["installation"] = "설치 기록을 읽을 수 없습니다"
    directories = [row["spec_path"] for row in baseline.get("features", [])]
    try:
        specs = project_path(root, "specs")
        if specs.is_dir():
            for entry in islice(specs.iterdir(), 100):
                name = f"specs/{entry.name}"
                if not entry.is_symlink() and entry.is_dir() and name not in directories:
                    directories.append(name)
        artifacts = discover_artifacts(root, directories, {row["path"] for row in (git_state or {}).get("files", [])})
    except ERRORS:
        artifacts = []
        alerts["artifacts"] = "일부 산출물 경로를 읽을 수 없습니다"
    evidence = {}
    for item in baseline.get("items", []):
        for gate in item["gates"]:
            for ref in gate["evidence"]:
                name = unquote(ref.partition("#")[0])
                evidence.setdefault(name, set()).add(gate["current"] or f"{gate['recorded']} 기록")
    for entry in artifacts:
        entry["gate_statuses"] = sorted(evidence.get(entry["path"], ()))
    return {"root": root.name, "observed_at": timestamp(), "git": git_state, "baseline": baseline,
            "artifacts": artifacts, "installation": installed, "alerts": alerts,
            "next_actions": next_actions(baseline, installed)}
