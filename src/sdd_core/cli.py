import argparse
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path
from uuid import UUID

from . import __version__
from .office import active_role
from .baseline import project_path, read_records, scaffold, validate
from .analysis import develop_check, record_analysis, register_feature
from .evidence import content_hash, verify_evidence
from .gates import (execute_gate, gate_status, prepare_gate_plan, register_gates,
                    require_gates, work_item)
from .lifecycle import prepare_retirement, retire
from .discovery import assess_discovery
from .version_sync import apply_sync, digest, install_skills, json_bytes, plan_sync, require_project
from .work_items import check_findings, expand_scope, read_plan, update
from . import reconciliation, revalidation, verification


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


def gate_confirmation(root, args, approval, mismatch):
    if args.ceo_confirm is not None:
        if args.ceo_confirm != approval:
            raise ValueError(mismatch)
        if not active_role(root, "ceo"):
            raise ValueError("현재 프로젝트의 CEO 승인이 꺼져 있거나 만료되었습니다")
        return True
    if args.confirm is not None and args.confirm != approval:
        raise ValueError(mismatch)
    return args.confirm is not None


from .concurrency import metadata_transaction


@metadata_transaction
def complete_work(root, identifier, filename):
    plan = read_plan(filename)
    actual = plan["actual_features"]
    if not isinstance(actual, list) or any(not isinstance(item, str) for item in actual):
        raise ValueError("actual_features에는 Feature UUID 목록이 필요합니다")
    require_project(root, scope=work_scope(root, identifier) + actual)
    _, current_item = work_item(root, identifier)
    if current_item.get("kind") != "reconciliation":
        develop_check(root, work_scope(root, identifier) + actual)
    check_findings(plan.get("findings"))
    if not plan["findings"]:
        raise ValueError("완료 영향 판정 근거가 필요합니다")
    _, item = work_item(root, identifier, editable=True)
    if set(actual) - set(item["declared_features"]):
        raise ValueError("실제 변경 범위를 선언 범위에 반영하고 Gate 집합을 재검토하세요")
    statuses = require_gates(root, item, "complete")
    evidence = verify_evidence(root, [row["ref"] for row in plan["evidence"]])
    inputs = {}
    for status in statuses:
        runs = item["gate_results"][status["id"]]
        inputs.update(runs[-1]["inputs"])
    if not inputs:
        raise ValueError("Gate 검증 입력 기록이 필요합니다")
    update(root, identifier, "completed", {
        "actual_features": actual, "findings": plan["findings"],
        "validation": {
            "status": "passed", "fingerprint": content_hash(inputs),
            "evidence": [{"ref": ref} for ref in evidence],
            "gate_status": statuses,
        },
    })


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sdd-core")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("uuid")
    commands.add_parser("validate")
    commands.add_parser("office-approval")
    commands.add_parser("scaffold")
    discovery = commands.add_parser("discovery-gate")
    discovery.add_argument("plan", type=Path)
    discovery.add_argument("--issue-id", action="store_true")
    hash_command = commands.add_parser("fingerprint")
    hash_command.add_argument("paths", nargs="+")
    start = commands.add_parser("start")
    start.add_argument("features", nargs="*")
    start.add_argument("--discovery",action="store_true")
    start.add_argument("--related", action="append", default=[])
    transition = commands.add_parser("transition")
    transition.add_argument("id")
    transition.add_argument("status", choices=["in_progress", "suspended", "failed"])
    finish = commands.add_parser("complete")
    finish.add_argument("id")
    finish.add_argument("plan", type=Path)
    preflight = commands.add_parser("preflight", help="Read-only installation and development entry checks")
    phases = preflight.add_subparsers(dest="phase", required=True)
    for phase in ("init", "develop"):
        check = phases.add_parser(phase)
        check.add_argument("--agent", required=True, choices=["codex", "claude"])
        if phase == "develop":
            check.add_argument("features", nargs="+")
        else:
            check.set_defaults(features=())
    version_check = commands.add_parser("version-check")
    version_check.add_argument("--agent", choices=["codex", "claude"])
    version_check.add_argument("features", nargs="*")
    sync = commands.add_parser("version-sync")
    sync.add_argument("plan", type=Path)
    sync.add_argument("--confirm", metavar="APPROVAL_HASH")
    for name in ("analysis-record", "feature-register"):
        commands.add_parser(name).add_argument("plan", type=Path)
    development = commands.add_parser("develop-check")
    development.add_argument("features", nargs="+")
    retirement = commands.add_parser("feature-retire")
    retirement.add_argument("id")
    retirement.add_argument("plan", type=Path)
    retirement.add_argument("--confirm")
    scope = commands.add_parser("scope-expand")
    scope.add_argument("id")
    scope.add_argument("plan", type=Path)
    scope.add_argument("--confirm")
    scope.add_argument('--apply',action='store_true')
    gates = commands.add_parser("gates")
    gates.add_argument("id")
    gates.add_argument("plan", type=Path)
    gates.add_argument("--confirm")
    gates.add_argument("--apply", action="store_true")
    gates.add_argument("--compose", action="store_true")
    gate_run = commands.add_parser("gate-run")
    gate_run.add_argument("id")
    gate_run.add_argument("gate")
    gate_run.add_argument("--review", type=Path)
    gate_run.add_argument("--force", action="store_true")
    stages = commands.add_parser("stage-check")
    stages.add_argument("id")
    stages.add_argument("stage", choices=["develop", "verify", "complete"])
    install = commands.add_parser("install-skills")
    install.add_argument("agent", choices=["codex", "claude"])
    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("plan", type=Path)
    reconcile.add_argument("--confirm")
    refresh = commands.add_parser("gate-refresh")
    refresh.add_argument("id")
    refresh.add_argument("--stage", choices=["develop", "verify", "complete"], default="complete")
    refresh.add_argument("--confirm")
    refresh.add_argument("--apply", action="store_true")
    policy = commands.add_parser('verification-policy')
    policy.add_argument('plan', type=Path)
    policy.add_argument('--apply', action='store_true')
    policy.add_argument('--confirm')
    profile = commands.add_parser('profile')
    profile.add_argument('id')
    profile.add_argument('plan', type=Path)
    profile.add_argument('--apply', action='store_true')
    profile.add_argument('--confirm')
    for delegated in (gates, refresh, policy, profile):
        delegated.add_argument("--ceo-confirm", metavar="APPROVAL_HASH")
    step = commands.add_parser('procedure')
    step.add_argument('id')
    step.add_argument('step', choices=sorted(verification.STEPS))
    step.add_argument('plan', type=Path)
    baseline_write=commands.add_parser('baseline-write')
    baseline_write.add_argument('name',choices=['project.md','architecture.md','decisions.md'])
    baseline_write.add_argument('plan',type=Path)
    commands.add_parser('source-map').add_argument('plan',type=Path)
    mode_parser=commands.add_parser('mode')
    mode_parser.add_argument('mode',nargs='?',choices=['direct','isolated'])
    mode_parser.add_argument('--runtime-root',type=Path)
    mode_parser.add_argument('--resolution-attempts',type=int)
    mode_parser.add_argument('--resolution-seconds',type=int)
    mode_parser.add_argument('--exclude',action='append')
    workspace=commands.add_parser('workspace')
    workspace.add_argument('action',choices=['list','create','enter','preview','queue','integrate','recover','discard','usage','cleanup'])
    workspace.add_argument('id',nargs='?')
    workspace.add_argument('--plan',type=Path)
    workspace.add_argument('--confirm')
    workspace.add_argument('--wait',action='store_true')
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"프로젝트 폴더가 아닙니다: {root}")
        if getattr(args, "ceo_confirm", None) is not None and (args.confirm is not None or args.apply):
            raise ValueError("--ceo-confirm은 --confirm 또는 --apply와 함께 사용할 수 없습니다")
        from . import workspaces
        if (workspaces.runtime_path(root)/'transaction.json').exists() and not(args.command=='workspace' and args.action=='recover'):
            workspaces.recover(root)
        if (workspaces.runtime_path(root)/'workspaces.json').exists():workspaces.prune_dead_workers(root)
        if args.command == 'mode':
            require_project(root)
            print(json.dumps(workspaces.mode(root,args.mode,runtime_root=args.runtime_root,limits={key:value for key,value in {'resolution_attempts':args.resolution_attempts,'resolution_seconds':args.resolution_seconds}.items() if value is not None} or None,exclude=args.exclude)));return 0
        if args.command == 'workspace':
            require_project(root,allow_quality_block=True)
            action=args.action
            if action=='list':result=workspaces.registry(root)
            elif action=='create':result=workspaces.create(root,args.id)
            elif action=='enter':result=workspaces.enter(root,args.id,read_plan(args.plan))
            elif action=='preview':
                with workspaces.project_lock(root,'integration'):result=workspaces.candidate(root,args.id,read_plan(args.plan) if args.plan else None)
            elif action=='queue':result=workspaces.queue(root,args.id)
            elif action=='integrate':result=workspaces.integrate(root,args.id,read_plan(args.plan) if args.plan else None,wait=args.wait)
            elif action=='recover':result=workspaces.recover(root)
            elif action=='discard':result=workspaces.discard(root,args.id,args.confirm)
            elif action=='usage':result=workspaces.inspect_runtime(root)
            elif action=='cleanup':result=workspaces.cleanup(root,args.confirm)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        workspaces.guard(root,args.command,getattr(args,'id',None))
        if args.command=='baseline-write':
            require_project(root)
            from .records import write_markdown
            plan=read_plan(args.plan);write_markdown(root,args.name,plan['expected_hash'],plan['text']);return 0
        if args.command=='source-map':
            require_project(root)
            from .records import update_sources
            plan=read_plan(args.plan);update_sources(root,plan['base'],plan['updated']);return 0
        if args.command == "office-approval":
            print(json.dumps({"ceo_gate_approval": active_role(root, "ceo")}))
        elif args.command == "uuid":
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
            if args.discovery:
                if args.features:raise ValueError('--discovery는 확정 Feature 없이 시작합니다')
                workspaces.start_discovery(root,identifier)
            else:
                develop_check(root, args.features)
                update(root, identifier, "pending", args.features, related=args.related)
            if workspaces.config(root)['mode']=='isolated':
                workspace=workspaces.create(root,identifier)
                print(json.dumps({'work_item':identifier,'workspace':workspace['workspace'],'entry':'blocked until workspace enter proof'}))
            else:print(identifier)
        elif args.command == "transition":
            if args.status == "in_progress":
                require_project(root, scope=work_scope(root, args.id))
            else:
                require_project(root, allow_quality_block=True)
            update(root, args.id, args.status)
        elif args.command == "complete":
            complete_work(root, args.id, args.plan)
        elif args.command == "analysis-record":
            require_project(root, allow_quality_block=True)
            record_analysis(root, read_plan(args.plan))
        elif args.command == "feature-register":
            require_project(root)
            print(register_feature(root, read_plan(args.plan), str(uuid7())))
        elif args.command == "develop-check":
            require_project(root, scope=args.features)
            develop_check(root, args.features)
            print("대상 Feature 개발 진입 Gate 통과")
        elif args.command == "scope-expand":
            plan = read_plan(args.plan)
            features = plan.get("features")
            if not isinstance(features, list) or any(not isinstance(value, str) for value in features):
                raise ValueError("범위 확장에는 Feature UUID 목록이 필요합니다")
            require_project(root, scope=work_scope(root, args.id) + features)
            _, item = work_item(root, args.id, editable=True)
            if args.apply:
                workspaces.bind_discovery(root,args.id,features,plan.get('reason'));return 0
            preview = {'work_item': args.id, 'record': content_hash(item), 'features': features,
                       'reason': plan.get('reason'), 'feature_state': content_hash(read_records(root, 'features.yaml', 'features'))}
            approval = content_hash(preview)
            if args.confirm is None:
                print(json_bytes({**preview, 'approval_hash': approval}).decode(), end='')
            elif args.confirm != approval:
                raise ValueError('승인한 범위 확대 입력이 변경됐습니다')
            else:
                expand_scope(root, args.id, features, plan.get('reason'))
        elif args.command == "gates":
            require_project(root, scope=work_scope(root, args.id))
            preview = prepare_gate_plan(root, args.id, read_plan(args.plan), compose_policy=args.compose)
            approval = content_hash(preview)
            if args.apply:
                if args.confirm or preview['approval_required']:
                    raise ValueError('필수 Gate 변경·완화에는 구체적 사용자 승인이 필요합니다')
                register_gates(root, args.id, preview)
                print(json_bytes({'status': 'applied', 'approval_required': False}).decode(), end='')
            elif gate_confirmation(root, args, approval, "승인한 Gate 정의/입력이 변경됐습니다"):
                register_gates(root, args.id, preview)
            else:
                print(json_bytes({**preview, "approval_hash": approval}).decode(), end="")
        elif args.command == "gate-run":
            require_project(root, scope=work_scope(root, args.id))
            _, current_item = work_item(root, args.id)
            if current_item.get("kind") != "reconciliation":
                develop_check(root, work_scope(root, args.id))
            result = execute_gate(root, args.id, args.gate,
                                  read_plan(args.review) if args.review else None, force=args.force)
            print(json_bytes(result).decode(), end="")
            if result["status"] != "PASS":
                return 2
        elif args.command == "stage-check":
            require_project(root, scope=work_scope(root, args.id))
            _, current_item = work_item(root, args.id)
            if current_item.get("kind") != "reconciliation":
                develop_check(root, work_scope(root, args.id))
            _, item = work_item(root, args.id)
            print(json_bytes(require_gates(root, item, args.stage)).decode(), end="")
        elif args.command == "feature-retire":
            require_project(root, allow_quality_block=True)
            preview, updated, writes = prepare_retirement(root, args.id, read_plan(args.plan))
            approval = content_hash(preview)
            if args.confirm is None:
                print(json_bytes({**preview, "approval_hash": approval}).decode(), end="")
            elif args.confirm != approval:
                raise ValueError("승인한 아카이브 입력이 변경됐습니다")
            else:
                retire(root, preview, updated, writes)
        elif args.command == "reconcile":
            config = read_plan(args.plan)
            require_project(root, scope=config.get("features"), validate_baseline=False)
            preview = reconciliation.prepare(root, config)
            approval = content_hash(preview)
            if args.confirm is None:
                print(json_bytes({**preview, "approval_hash": approval}).decode(), end="")
            elif args.confirm != approval:
                raise ValueError("승인한 정합화 기준·입력·범위·변경안이 달라졌습니다. 새 승인이 필요합니다")
            else:
                print(json_bytes(reconciliation.apply(root, preview, str(uuid7()))).decode(), end="")
        elif args.command == "gate-refresh":
            require_project(root, scope=work_scope(root, args.id), validate_baseline=False)
            preview = revalidation.prepare(root, args.id, args.stage)
            approval = content_hash(preview)
            if args.apply and (args.confirm or preview['renames'] or preview['ambiguous']):
                raise ValueError('이름 변경·모호한 검증 입력은 구체적 승인이 필요합니다')
            confirmed = gate_confirmation(root, args, approval, "선택적 재검증 입력·이름 변경 후보가 바뀌었습니다. 새 승인이 필요합니다")
            if not confirmed and not args.apply:
                print(json_bytes({**preview, "approval_hash": approval}).decode(), end="")
            else:
                result = revalidation.refresh(root, args.id, preview)
                print(json_bytes(result).decode(), end="")
                if result["status"] != "PASS":
                    return 2
        elif args.command in ('verification-policy', 'profile'):
            require_project(root, scope=work_scope(root, args.id) if args.command == 'profile' else None)
            config = read_plan(args.plan)
            preview = verification.profile_preview(root, args.id, config) if args.command == 'profile' else verification.registry_preview(root, config)
            approval = content_hash(preview)
            if args.apply and (args.confirm or preview['approval_required']):
                raise ValueError('이 변경은 자동 적용 대상이 아닙니다. 구체적 사용자 승인을 받으세요')
            confirmed = gate_confirmation(root, args, approval, '승인한 정책·프로파일 입력이 변경됐습니다')
            if args.apply or confirmed:
                if args.command == 'profile':
                    verification.apply_profile(root, args.id, preview, delegated=args.ceo_confirm is not None)
                else:
                    verification.apply_registry(root, preview)
                print(json_bytes({'status': 'applied', 'approval_required': preview['approval_required']}).decode(), end='')
            else:
                print(json_bytes({**preview, 'approval_hash': approval}).decode(), end='')
        elif args.command == 'procedure':
            require_project(root, scope=work_scope(root, args.id))
            verification.record_step(root, args.id, args.step, read_plan(args.plan))
        elif args.command == "install-skills":
            install_skills(root, args.agent)
        elif args.command == "preflight":
            require_project(root, args.agent, args.features)
            if args.phase == "init" and workspaces.reference(root) is None and workspaces.config(root)["mode"]=="isolated" and workspaces.active(root):
                raise ValueError("활성 격리 작업 중 원본 초기화 변경을 차단합니다")
            if args.phase == "develop":
                develop_check(root, args.features)
            print(json.dumps({"phase": args.phase, "core_version": __version__,
                              "agent": args.agent, "features": args.features, "status": "PASS"}))
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
