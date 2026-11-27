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
RUNNER = ".specify/sdd-core"
BASELINE = ".specify/baseline/"
FOLDERS = {"codex": ".agents", "claude": ".claude"}
ACTIVE = ("sdd-init", "sdd-develop", "sdd-sync", "sdd-mode")
RETIRED = "sdd-commit"
LEGACY_HASHES = {
    "sdd-mode": set(),
    "sdd-init": {
        "a702f48ca9634570d08e7e1f7ab0ed0e6d9f930fec0fe86cce2b0717e9942705",
        "3ad4eb0792b88eafd07d7c7d5a5288664268b562ae05a79c2634b5e40d5fc865",
        "93c4dbae17c47ef3d19d8adc6e82908285695108c8dffe13b57d9bf14a097e34",
        "9d1985ff03e94b7b74a316e15207b6f7c3e5b3e46b249ca00d6ba438c4921eb0",
        "b593e7cc40ec14886ca2cce690705e4c888ac729aabc62718efe1136333f034c",
        "352e1edb4690ddd6d8fb626a6ccf4948aa1cf801edb41bb78e5fdf1051b02e96",
        "f53a9d176581852c9c518dbe01b95c60684ee7eda030dad2e011225168691031",
        "66311a9176a00971f44b74ed7c196a4a209a8ac51ddde7d7230b180f6cfa7f2d",
        "c04b4c41ef5b1796178ddd7626b6837eed784091168b6e781eb869072bc029bc",
        "8aed08fb376b14dbd36a52ad1d01a080254383f5955520165fbb328b3465b2e2",
    },
    "sdd-develop": {
        "5c1c09e08e3a84684936f5e22ec114746206d550308d3d00c24977d38c69a68e",
        "c5e4509e85dd35aa20e4e7fd5ba4d50fb71b9871324b3388f41efc44d17eb78c",
        "22af0785c02b4d460053386a6cfc5e542360f5c3b2bd0b0cbac00f8331ba298d",
        "6d61ce1ed74dd7712b2b9041e054e1e77d542e0b6ec0a25fcf9402da05791cad",
        "7aef15211c743d34dafb63b867aa908b99cbfa3a3cdbfd40bfa68b2ba2ab3baf",
        "fabd33d0a39727375f209ed982c56d0fa3b263292dedad11f7f8b002e7e90db0",
        "cbcf050225624c79756635eb65cff78baec8d72c27e6bfda986acfc33791ba0c",
        "aa1c89893dfb4b5e24664888a6e262fe30b91fc294ef00f1cfc925e5d071d595",
        "dcfd91eba334c1f1872e82e45143d80c78694c70d9277ffca0c3e785eb3e55e9",
        "377b6f6defc8e9c0fa8c47df90a38c43cb94a9910e0f50f60efe850d1f4889a0",
        "73f439156645c2ee0b36f703b58256653e00634f6a7e145dc13d3fee4fa7b3bc",
    },
    "sdd-sync": {
        "9e1ec8a78aee383badc524307d0cd8e2b14e7397442065aae6e2dc5c493785ae",
        "a6ea26b5d0d16617a94742ed48df4370cb72444bdbe301f5e280e07fbb49782d",
        "bc873b8d758c60091da732accbee7c773b2b29a1a6e21ec0369bc8132ba687c2",
        "fdf79f730c3a29af08c15f6576f160ccf4a269656902aac5a3ab251ea71819bd",
        "99a4449d454ebff72bddb0994355846e389f59e2aeef68a31c5ffe21ae829c13",
        "ccb370626b4ce00b028c37473504807f1af90da6d894b1246b9720685682fd5e",
        "30750497bdaa1743657d467fb78816dd6d4dffc4882e81476029592238b389ba",
        "4f1aa59fb18144fccf7112001b8e0e5bc90104363d4759b307ebdd0be6eef3d4",
        "b418997815ac92a3cccfdad473e6ae7249e4793a23636fc14437c2cd2a7595af",
        "e8527ad808b217bb2e7bf9687b3e4a0cd5541bab1600db6421b5a73a3d97d916",
    },
    RETIRED: {"a0845458f6d89eca648c37974745de424f707e86684d3b102ac4e345410d6b92"},
}
MIGRATIONS = {
    "0.1.0": ("0.2.0", "path-only-source-map"),
    "0.2.0": ("0.3.0", "feature-lifecycle-and-gates"),
    "0.3.0": ("0.4.0", "approved-reconciliation-and-selective-revalidation"),
    "0.4.0": ("0.5.0", "risk-profiles-and-reusable-verification"),
    "0.5.0": ("0.5.1", "scoped-development-skill-policy"),
    "0.5.1": ("0.6.0", "isolated-work-items-and-cooperative-concurrency"),
}


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
            if name == RUNNER:
                path.chmod(0o755)
        finally:
            temporary.unlink(missing_ok=True)


def skill_path(agent, name):
    return f"{FOLDERS[agent]}/skills/{name}/SKILL.md"


def skill_marker(agent):
    return f"{FOLDERS[agent]}/skills/.spec-thread.json"


def bundle():
    resource = files("sdd_core").joinpath("skills")
    conversation = resource.joinpath("_conversation.md").read_bytes()
    return {name: resource.joinpath(f"{name}.md").read_bytes().rstrip() + b"\n\n" + conversation
            for name in ACTIVE}


def skill_record(agent, skills):
    return {"agent": agent, "core_version": __version__, "skills": {
        name: digest(contents) for name, contents in skills.items()
    }}


def runner_bytes():
    package = str(Path(__file__).resolve().parents[1])
    text = ("#!/usr/bin/env python3\n# SpecThread managed project runner\n"
            "import os, sys\n"
            f"python = {sys.executable!r}\n"
            f"package = {package!r}\n"
            "if os.path.abspath(sys.executable) != os.path.abspath(python):\n"
            "    os.execv(python, [python, __file__, *sys.argv[1:]])\n"
            "sys.path.insert(0, package)\n"
            "from sdd_core.cli import main\n"
            "sys.exit(main())\n")
    return text.encode('utf-8')


def runner_output(root, project):
    contents = runner_bytes()
    existing = read_file(root, RUNNER)
    if existing is not None and existing != contents:
        if project is None or digest(existing) != project.get('runner_hash'):
            raise ValueError('프로젝트 Core 실행 파일이 사용자 수정본입니다. 덮어쓰지 않습니다')
    return contents


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
    paths[RUNNER] = runner_output(root, project)
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
    return {"agent": agent, "core_version": __version__, "runner_hash": digest(runner_bytes()), "quality": {
        "global_blocked": global_blocked, "restricted_features": restricted_features,
    }}


def require_project(root, agent=None, scope=None, *, allow_quality_block=False, validate_baseline=True):
    project = read_marker(root, PROJECT)
    if project is None or project.get("core_version") != __version__:
        raise ValueError("Core·Project 버전 불일치 또는 미등록. install-skills/version-sync를 확인하세요.")
    agent = installed_agent(root, agent, project)
    require_skills(root, agent)
    if read_file(root, RUNNER) != runner_bytes() or project.get("runner_hash") != digest(runner_bytes()):
        raise ValueError("프로젝트 Core 실행 환경이 바뀌었습니다. update 또는 version-sync를 실행하세요")
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
        states = {row["id"]: row.get("status") for row in read_records(root, "features.yaml", "features")}
        if any(states[name] != "active" for name in scope):
            raise ValueError("작업 범위에 폐기된 Feature가 있습니다")
    if validate_baseline and project_path(root, BASELINE + "features.yaml").is_file():
        validate(root)
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
    from .workspaces import update_blockers
    blockers=update_blockers(root)
    if blockers:raise ValueError(f"활성 Workspace/트랜잭션으로 업데이트 차단: {blockers}")
    validate(root, legacy=True)
    if read_file(root, BASELINE + "verification.yaml") is not None:
        from .verification import registry
        registry(root, configured=False)
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
    runner = runner_output(root, project)
    if read_file(root, RUNNER) != runner:
        outputs[RUNNER] = runner
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

    if any(step["migration"] == "feature-lifecycle-and-gates" for step in steps):
        source_name = BASELINE + "features.yaml"
        document = yaml.load(read_file(root, source_name), Loader=BaselineLoader)
        version = document.get("schema_version")
        if version is not None and (type(version) is not int or version != 1):
            raise ValueError("미지원 Baseline 스키마입니다")
        if version is None:
            document["schema_version"] = 1
            document["analysis"] = {"status": "not_started", "unanalysed": []}
            document.setdefault("path_redirects", {})
            for feature in document["features"]:
                feature.setdefault("status", "active")
            outputs[source_name] = yaml.safe_dump(
                document, allow_unicode=True, sort_keys=False,
            ).encode("utf-8")
    if any(step['migration'] == 'risk-profiles-and-reusable-verification' for step in steps):
        if read_file(root, BASELINE + 'verification.yaml') is None:
            from .verification import empty_registry
            outputs[BASELINE + 'verification.yaml'] = yaml.safe_dump(empty_registry(), allow_unicode=True, sort_keys=False).encode('utf-8')
    if read_file(root, BASELINE + "features.yaml") is not None and not steps:
        validate(root)

    for name in (*outputs, PROJECT):
        managed_path(root, name)

    all_features = read_records(root, "features.yaml", "features")
    features = [feature for feature in all_features if feature.get("status", "active") == "active"]
    checks = quality_plan(config, {feature["id"] for feature in features})
    validation_paths = {
        PROJECT, RUNNER, skill_marker(agent), *(skill_path(agent, name) for name in (*ACTIVE, RETIRED)),
        *(BASELINE + name for name in ("project.md", "architecture.md", "decisions.md",
                                        "features.yaml", "source-map.yaml", "work-items.yaml", "verification.yaml")),
        *(f"{feature['spec_path']}/{name}" for feature in all_features for name in ("spec.md", "plan.md")),
        *(name for row in read_records(root, "source-map.yaml", "mappings")
          if row["feature_id"] in {feature["id"] for feature in features}
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
        old_record=read_marker(root,PROJECT) or {}
        record = project_record(plan["agent"], global_blocked, sorted(restricted))
        if 'development' in old_record:record['development']=old_record['development']
        write_file(root, PROJECT, json_bytes(record))
    except (OSError, ValueError) as error:
        raise ValueError(f"동기화 확정 실패. 사용자 원복 후 처음부터 재시도: {error}") from error
    return {
        "mandatory": "passed", "quality": "blocked" if global_blocked else "limited" if restricted else "passed",
        "restricted_features": sorted(restricted), "checks": results,
        "changed_paths": [*outputs, PROJECT],
    }
