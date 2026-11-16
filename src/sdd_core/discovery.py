from .baseline import mapping, nonempty


def assess_discovery(plan):
    mode = plan.get("mode")
    if mode not in ("greenfield", "brownfield"):
        raise ValueError("Discovery mode는 greenfield 또는 brownfield여야 합니다")

    candidate = nonempty(plan.get("candidate"), "candidate")
    required = {"scope", "boundaries", "requirements", "spec_quality"}
    required.add("workflow" if mode == "greenfield" else "current_behavior")
    checks = mapping(plan.get("checks"), "checks")
    missing = required - checks.keys()
    if missing:
        raise ValueError("누락된 Discovery 점검: " + ", ".join(sorted(missing)))

    findings = []
    verdict = "READY"
    for name, check in checks.items():
        nonempty(name, "check")
        check = mapping(check, name)
        status = check.get("status")
        if status not in ("verified", "condition", "blocked"):
            raise ValueError(f"{name}: verified, condition 또는 blocked 판정이 필요합니다")
        evidence = nonempty(check.get("evidence"), f"{name}.evidence")
        if status == "verified":
            continue
        next_step = nonempty(check.get("next_step"), f"{name}.next_step")
        if status == "condition" and check.get("critical") is not False:
            status = "blocked"
        if status == "blocked":
            verdict = "BLOCKED"
        elif verdict == "READY":
            verdict = "CONDITIONAL"
        findings.append({"check": name, "status": status, "evidence": evidence, "next_step": next_step})

    return {"candidate": candidate, "verdict": verdict, "findings": findings}
