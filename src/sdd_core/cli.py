import argparse
import hashlib
from importlib.resources import files
import json
import secrets
import sys
import time
from pathlib import Path
from uuid import UUID

from .baseline import project_path, scaffold, validate
from .checks import run_checks
from .discovery import assess_discovery
from .integration import integrate
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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sdd-core")
    parser.add_argument("--root", type=Path, default=Path.cwd())
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
    for command in ("preview", "commit"):
        commands.add_parser(command).add_argument("plan", type=Path)
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
            scaffold(root)
        elif args.command == "discovery-gate":
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
            identifier = str(uuid7())
            update(root, identifier, "pending", args.features)
            print(identifier)
        elif args.command == "transition":
            update(root, args.id, args.status)
        elif args.command == "complete":
            plan = read_plan(args.plan)
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
            folder = ".agents" if args.agent == "codex" else ".claude"
            for skill in files("sdd_core").joinpath("skills").iterdir():
                target = project_path(root, f"{folder}/skills/{skill.name.removesuffix('.md')}/SKILL.md")
                target.parent.mkdir(parents=True, exist_ok=True)
                contents = skill.read_bytes()
                try:
                    with target.open("xb") as stream:
                        stream.write(contents)
                except FileExistsError:
                    if target.read_bytes() != contents:
                        raise ValueError(f"기존 Skill과 충돌합니다: {target}") from None
        elif args.command == "preview":
            print(json.dumps(integrate(root, read_plan(args.plan), preview=True), ensure_ascii=False))
        elif args.command == "commit":
            print(integrate(root, read_plan(args.plan)))
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
