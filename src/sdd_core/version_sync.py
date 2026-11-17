import hashlib
import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from . import __version__
from .baseline import BaselineLoader, mapping, nonempty, project_path, read_records, source_paths, validate
from .checks import check_commands

PROJECT = ".specify/spec-thread.json"
BASELINE = ".specify/baseline/"
FOLDERS = {"codex": ".agents", "claude": ".claude"}
ACTIVE = ("sdd-init", "sdd-develop", "sdd-sync")
RETIRED = "sdd-commit"
LEGACY_HASHES = {
    "sdd-init": {
        "66311a9176a00971f44b74ed7c196a4a209a8ac51ddde7d7230b180f6cfa7f2d",
        "c04b4c41ef5b1796178ddd7626b6837eed784091168b6e781eb869072bc029bc",
        "8aed08fb376b14dbd36a52ad1d01a080254383f5955520165fbb328b3465b2e2",
    },
    "sdd-develop": {
        "377b6f6defc8e9c0fa8c47df90a38c43cb94a9910e0f50f60efe850d1f4889a0",
        "73f439156645c2ee0b36f703b58256653e00634f6a7e145dc13d3fee4fa7b3bc",
    },
    "sdd-sync": {
        "b418997815ac92a3cccfdad473e6ae7249e4793a23636fc14437c2cd2a7595af",
        "e8527ad808b217bb2e7bf9687b3e4a0cd5541bab1600db6421b5a73a3d97d916",
    },
    RETIRED: {"a0845458f6d89eca648c37974745de424f707e86684d3b102ac4e345410d6b92"},
}
MIGRATIONS = {"0.1.0": ("0.2.0", "path-only-source-map")}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def read_file(root, name):
    path = project_path(root, name)
    return path.read_bytes() if path.exists() else None


def read_marker(root, name):
    data = read_file(root, name)
    return mapping(json.loads(data), name) if data is not None else None


def managed_path(root, name):
    path = project_path(root, name)
    if path != root.resolve() / name:
        raise ValueError(f"관리 파일은 심볼릭 링크를 사용할 수 없습니다: {name}")
    return path


def write_file(root, name, contents):
    path = managed_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(contents)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def skill_path(agent, name):
    return f"{FOLDERS[agent]}/skills/{name}/SKILL.md"


def skill_marker(agent):
    return f"{FOLDERS[agent]}/skills/.spec-thread.json"


def bundle():
    resource = files("sdd_core").joinpath("skills")
    return {name: resource.joinpath(f"{name}.md").read_bytes() for name in ACTIVE}


def skill_record(agent, skills):
    return {"agent": agent, "core_version": __version__, "skills": {
        name: digest(contents) for name, contents in skills.items()
    }}


def require_skills(root, agent):
    skills = bundle()
    if read_marker(root, skill_marker(agent)) != skill_record(agent, skills):
        raise ValueError("Skill 버전/설치 기록 불일치. version-sync 계획을 검토하세요.")
    for name, contents in skills.items():
        if read_file(root, skill_path(agent, name)) != contents:
            raise ValueError(f"설치 Skill 내용 불일치: {name}")
    if read_file(root, skill_path(agent, RETIRED)) is not None:
        raise ValueError("폐기된 sdd-commit Skill이 남아 있습니다")


def installed_agent(root, requested, project):
    agents = {
        agent for agent in FOLDERS if read_file(root, skill_marker(agent)) is not None
        or any(read_file(root, skill_path(agent, name)) is not None for name in (*ACTIVE, RETIRED))
    }
    if project is not None:
        agents.add(project.get("agent"))
    if requested is not None:
        agents.add(requested)
    if len(agents) != 1 or next(iter(agents), None) not in FOLDERS:
        raise ValueError("프로젝트에 사용할 Harness 에이전트 한 종류를 지정하세요")
    return agents.pop()


def install_skills(root, agent):
    if not project_path(root, ".specify").is_dir():
        raise ValueError("대상 프로젝트에 공식 Spec Kit를 먼저 초기화하세요")
    project = read_marker(root, PROJECT)
    installed_agent(root, agent, project)
    if project is not None and project.get("core_version") != __version__:
        raise ValueError("기존 Project 버전은 version-sync로 동기화하세요")
    if project is None and project_path(root, BASELINE.rstrip("/")).exists():
        raise ValueError("기존 Baseline에는 출발 버전을 확인한 뒤 version-sync를 사용하세요")
    skills = bundle()
    previous = read_marker(root, skill_marker(agent))
    if (project is not None or previous is not None) and previous != skill_record(agent, skills):
        raise ValueError("기존 Skill은 version-sync로 동기화하세요")
    paths = {skill_path(agent, name): contents for name, contents in skills.items()}
    for name in (*paths, PROJECT, skill_marker(agent)):
        managed_path(root, name)
    for name, contents in paths.items():
        existing = read_file(root, name)
        if existing is not None and existing != contents:
            raise ValueError(f"기존 Skill과 충돌합니다: {name}")
    if read_file(root, skill_path(agent, RETIRED)) is not None:
        raise ValueError("기존 sdd-commit은 version-sync로 정리하세요")
    for name, contents in paths.items():
        if read_file(root, name) is None:
            write_file(root, name, contents)
    if previous is None:
        write_file(root, skill_marker(agent), json_bytes(skill_record(agent, skills)))
    if project is None:
        write_file(root, PROJECT, json_bytes(project_record(agent, False, [])))
    require_skills(root, agent)


def project_record(agent, global_blocked, restricted_features):
    return {"agent": agent, "core_version": __version__, "quality": {
        "global_blocked": global_blocked, "restricted_features": restricted_features,
    }}


def require_project(root, agent=None, scope=None, *, allow_quality_block=False):
    project = read_marker(root, PROJECT)
    if project is None or project.get("core_version") != __version__:
        raise ValueError("Core·Project 버전 불일치 또는 미등록. install-skills/version-sync를 확인하세요.")
    agent = installed_agent(root, agent, project)
    require_skills(root, agent)
    quality = mapping(project.get("quality"), "quality")
    limited = quality.get("restricted_features")
    globally_limited = quality.get("global_blocked")
    if not isinstance(limited, list) or not all(isinstance(item, str) and item for item in limited):
        raise ValueError("Project 품질 제한 기록이 잘못되었습니다")
    if not isinstance(globally_limited, bool):
        raise ValueError("Project 전역 품질 기록이 잘못되었습니다")
    if not allow_quality_block and (globally_limited or (limited and (not scope or set(scope).intersection(limited)))):
        raise ValueError("품질 Gate에 의해 이 범위가 제한됩니다. version-sync로 재검증하세요.")
    if scope:
        identifiers = {record["id"] for record in read_records(root, "features.yaml", "features")}
        if set(scope) - identifiers:
            raise ValueError("작업 범위에 등록되지 않은 Feature가 있습니다")
    return project


def migration_path(source):
    result = []
    visited = set()
    while source != __version__:
        if source in visited or source not in MIGRATIONS:
            raise ValueError(f"{source} → {__version__}의 로컬 누적 변경 경로가 없습니다")
        visited.add(source)
        target, migration = MIGRATIONS[source]
        result.append({"from": source, "to": target, "migration": migration})
        source = target
    return result


def quality_plan(config, identifiers):
    checks = config.get("quality")
    if not isinstance(checks, list) or not checks:
        raise ValueError("기존 프로젝트의 검증 명령을 quality에 지정하세요")
    for check in checks:
        check = mapping(check, "quality check")
        check_commands([check.get("command")])
        features = check.get("features")
        if not isinstance(features, list) or any(
            not isinstance(identifier, str) or identifier not in identifiers
            for identifier in features
        ):
            raise ValueError("품질 검사 features에는 기존 UUID를 넣으세요. []는 전역 검사입니다.")
        paths = check.get("paths")
        if not isinstance(paths, list) or not paths:
            raise ValueError("품질 검사 입력 파일 paths가 필요합니다")
        for path in paths:
            nonempty(path, "quality.paths")
    if not any(not check["features"] for check in checks):
        covered = {identifier for check in checks for identifier in check["features"]}
        if identifiers - covered:
            raise ValueError("품질 검사는 전체 Feature 또는 전역 범위를 포함해야 합니다")
    return checks


def snapshot(root, paths):
    result = {}
    for name in sorted(paths):
        data = read_file(root, name)
        result[name] = digest(data) if data is not None else None
    return result


def plan_sync(root, config):
    validate(root)
    project = read_marker(root, PROJECT)
    agent = installed_agent(root, config.get("agent"), project)
    from_version = config.get("from_version")
    if project is None:
        if from_version != "0.1.0":
            raise ValueError("표식 없는 기존 설치는 출발 버전 0.1.0을 직접 확인해 from_version에 지정하세요")
    else:
        recorded = nonempty(project.get("core_version"), "core_version")
        if from_version is not None and from_version != recorded:
            raise ValueError("from_version이 Project 기록과 다릅니다")
        from_version = recorded

    steps = migration_path(from_version)
    skills = bundle()
    skill_info = read_marker(root, skill_marker(agent))
    skill_version = skill_info.get("core_version") if skill_info is not None else None
    if skill_info is not None and skill_info.get("agent") != agent:
        raise ValueError("Skill과 Project의 에이전트 기록이 다릅니다")
    if skill_version is not None:
        migration_path(nonempty(skill_version, "Skill core_version"))

    outputs = {}
    for name in (*ACTIVE, RETIRED):
        path = skill_path(agent, name)
        existing = read_file(root, path)
        replacement = skills.get(name)
        if existing == replacement:
            continue
        if existing is not None and digest(existing) not in LEGACY_HASHES[name]:
            raise ValueError(f"사용자 수정 또는 출처 미확인 Skill: {path}")
        outputs[path] = replacement

    if skill_info != skill_record(agent, skills):
        outputs[skill_marker(agent)] = json_bytes(skill_record(agent, skills))

    source_map = BASELINE + "source-map.yaml"
    for step in steps:
        if step["migration"] == "path-only-source-map":
            rows = read_records(root, "source-map.yaml", "mappings")
            paths_only = [{**row, "sources": [{"path": name} for name in source_paths(row["sources"])]}
                          for row in rows]
            if rows != paths_only:
                document = yaml.load(read_file(root, source_map), Loader=BaselineLoader)
                document["mappings"] = paths_only
                outputs[source_map] = yaml.safe_dump(
                    document, allow_unicode=True, sort_keys=False,
                ).encode("utf-8")

    for name in (*outputs, PROJECT):
        managed_path(root, name)

    features = read_records(root, "features.yaml", "features")
    checks = quality_plan(config, {feature["id"] for feature in features})
    validation_paths = {
        PROJECT, skill_marker(agent), *(skill_path(agent, name) for name in (*ACTIVE, RETIRED)),
        *(BASELINE + name for name in ("project.md", "architecture.md", "decisions.md",
                                        "features.yaml", "source-map.yaml", "work-items.yaml")),
        *(f"{feature['spec_path']}/{name}" for feature in features for name in ("spec.md", "plan.md")),
        *(name for row in read_records(root, "source-map.yaml", "mappings")
          for name in source_paths(row["sources"])),
    }
    for check in checks:
        for name in check["paths"]:
            if not project_path(root, name).is_file():
                raise ValueError(f"품질 검사 입력 파일이 없습니다: {name}")
            validation_paths.add(name)
    plan = {
        "agent": agent, "core": __version__, "project": from_version, "skill": skill_version,
        "migrations": steps, "affected_features": [feature["id"] for feature in features],
        "changes": {name: digest(contents) if contents is not None else None
                    for name, contents in outputs.items()},
        "project_record": PROJECT, "quality": checks, "inputs": snapshot(root, validation_paths),
    }
    return plan, outputs, features


def apply_sync(root, plan, outputs, features):
    try:
        for name, contents in outputs.items():
            if contents is None:
                managed_path(root, name).unlink()
            else:
                write_file(root, name, contents)
        require_skills(root, plan["agent"])
        validate(root)
    except (OSError, ValueError) as error:
        raise ValueError(f"필수 Gate 실패. 변경 자료를 사용자 Git으로 원복한 뒤 처음부터 재시도: {error}") from error

    before = snapshot(root, plan["inputs"])
    results = []
    restricted = set()
    global_blocked = False
    for check in plan["quality"]:
        try:
            run = subprocess.run(check["command"], cwd=root, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, errors="replace")
            if run.stdout:
                print(run.stdout, end="", file=sys.stderr)
            result = {"command": check["command"], "features": check["features"], "exit_code": run.returncode}
        except OSError as error:
            result = {"command": check["command"], "features": check["features"], "error": str(error)}
        results.append(result)
        if result.get("exit_code") != 0:
            restricted.update(check["features"])
            global_blocked |= not check["features"]

    pending = True
    while pending:
        previous = len(restricted)
        restricted.update(
            feature["id"] for feature in features
            if any(dependency["feature_id"] in restricted for dependency in feature["dependencies"])
        )
        pending = len(restricted) != previous

    if before != snapshot(root, plan["inputs"]):
        raise ValueError("품질 검사 중 검증 입력이 달라졌습니다. 사용자 원복 후 처음부터 재시도하세요.")
    try:
        validate(root)
        require_skills(root, plan["agent"])
        record = project_record(plan["agent"], global_blocked, sorted(restricted))
        write_file(root, PROJECT, json_bytes(record))
    except (OSError, ValueError) as error:
        raise ValueError(f"동기화 확정 실패. 사용자 원복 후 처음부터 재시도: {error}") from error
    return {
        "mandatory": "passed", "quality": "blocked" if global_blocked else "limited" if restricted else "passed",
        "restricted_features": sorted(restricted), "checks": results,
        "changed_paths": [*outputs, PROJECT],
    }
