import argparse
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path
from uuid import UUID

from . import __version__
from .baseline import project_path, read_records, scaffold, validate
from .checks import run_checks
from .discovery import assess_discovery
from .version_sync import apply_sync, digest, install_skills, json_bytes, plan_sync, require_project
from .work_items import check_findings, read_plan, update


def uuid7():
    timestamp = time.time_ns() // 1_000_000
    bits = timestamp << 80
    bits |= 7 << 76 | secrets.randbits(12) << 64
    bits |= 2 << 62 | secrets.randbits(62)
    return UUID(int=bits)


def fingerprint(root, paths):
    entries = []
    for name in sorted(set(paths)):
        path = project_path(root, name)
        if not path.is_file():
            raise ValueError(f"검증 대상 파일이 없습니다: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        entries.append([name, digest])
    encoded = json.dumps(entries, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def work_scope(root, identifier):
    for record in read_records(root, "work-items.yaml", "work_items"):
        if record["id"] == identifier:
            return record["declared_features"] + record["actual_features"]
    raise ValueError(f"Work Item을 찾을 수 없습니다: {identifier}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sdd-core")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("uuid")
    commands.add_parser("validate")
    commands.add_parser("scaffold")
    discovery = commands.add_parser("discovery-gate")
    discovery.add_argument("plan", type=Path)
    discovery.add_argument("--issue-id", action="store_true")
    hash_command = commands.add_parser("fingerprint")
    hash_command.add_argument("paths", nargs="+")
    start = commands.add_parser("start")
    start.add_argument("features", nargs="*")
    transition = commands.add_parser("transition")
    transition.add_argument("id")
    transition.add_argument("status", choices=["in_progress", "suspended", "failed"])
    finish = commands.add_parser("complete")
    finish.add_argument("id")
    finish.add_argument("plan", type=Path)
    version_check = commands.add_parser("version-check")
    version_check.add_argument("--agent", choices=["codex", "claude"])
    version_check.add_argument("features", nargs="*")
    sync = commands.add_parser("version-sync")
    sync.add_argument("plan", type=Path)
    sync.add_argument("--confirm", metavar="APPROVAL_HASH")
    install = commands.add_parser("install-skills")
    install.add_argument("agent", choices=["codex", "claude"])
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"프로젝트 폴더가 아닙니다: {root}")
        if args.command == "uuid":
            print(uuid7())
        elif args.command == "scaffold":
            require_project(root)
            scaffold(root)
        elif args.command == "discovery-gate":
            if args.issue_id:
                require_project(root)
            result = assess_discovery(read_plan(args.plan))
            if args.issue_id and result["verdict"] == "READY":
                result["feature_id"] = str(uuid7())
            print(json.dumps(result, ensure_ascii=False))
            if args.issue_id and "feature_id" not in result:
                return 2
        elif args.command == "validate":
            validate(root)
            print("Baseline 검증 통과")
        elif args.command == "fingerprint":
            print(fingerprint(root, args.paths))
        elif args.command == "start":
            require_project(root, scope=args.features)
            identifier = str(uuid7())
            update(root, identifier, "pending", args.features)
            print(identifier)
        elif args.command == "transition":
            if args.status == "in_progress":
                require_project(root, scope=work_scope(root, args.id))
            else:
                require_project(root, allow_quality_block=True)
            update(root, args.id, args.status)
        elif args.command == "complete":
            plan = read_plan(args.plan)
            actual = plan["actual_features"]
            if not isinstance(actual, list) or any(not isinstance(item, str) for item in actual):
                raise ValueError("actual_features에는 Feature UUID 목록이 필요합니다")
            require_project(root, scope=work_scope(root, args.id) + actual)
            check_findings(plan.get("findings"))
            paths = plan["paths"]
            if not isinstance(paths, list) or not paths:
                raise ValueError("Fingerprint 검증 경로가 필요합니다")
            before = fingerprint(root, paths)
            run_checks(root, plan.get("checks"))
            if before != fingerprint(root, paths):
                raise ValueError("검증 도중 입력 파일이 변경됐습니다")
            update(root, args.id, "completed", {
                "actual_features": plan["actual_features"],
                "findings": plan["findings"],
                "validation": {
                    "status": "passed",
                    "fingerprint": before,
                    "evidence": plan["evidence"],
                },
            })
        elif args.command == "install-skills":
            install_skills(root, args.agent)
        elif args.command == "version-check":
            require_project(root, args.agent, args.features)
            print(f"Core·Project·Skill {__version__} 일치")
        elif args.command == "version-sync":
            plan, outputs, features = plan_sync(root, read_plan(args.plan))
            approval = digest(json_bytes(plan))
            if args.confirm is None:
                print(json_bytes({**plan, "approval_hash": approval}).decode(), end="")
            else:
                if args.confirm != approval:
                    raise ValueError("승인한 버전 동기화 입력이 달라졌습니다. 새 계획을 검토하세요.")
                result = apply_sync(root, plan, outputs, features)
                print(json_bytes(result).decode(), end="")
                if result["quality"] == "blocked":
                    return 2
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
