from .baseline import mapping, nonempty, sequence, validate
from .discovery import assess_discovery
from .evidence import content_hash, input_files, verify_evidence
from .records import read_document, write_document
from .work_items import check_findings


def feature_basis(feature):
    return content_hash({key: feature[key] for key in ("id", "status", "spec_path", "dependencies")})


def record_analysis(root, plan):
    validate(root)
    document = read_document(root, "features.yaml")
    status = plan.get("status")
    if status not in ("not_started", "partial", "complete"):
        raise ValueError("분석 상태는 not_started, partial, complete입니다")
    unanalysed = sequence(plan.get("unanalysed"), "unanalysed")
    if any(not isinstance(name, str) or not name.strip() for name in unanalysed):
        raise ValueError("미분석 범위에는 설명이 필요합니다")
    if status == "complete" and unanalysed:
        raise ValueError("complete에는 미분석 범위가 남을 수 없습니다")
    if ".specify/baseline/features.yaml" in sequence(plan.get("paths"), "paths"):
        raise ValueError("분석 기록 자체를 입력으로 쓰지 말고 원본 명세·근거 파일을 지정하세요")
    inputs = input_files(root, plan.get("paths"))
    evidence = verify_evidence(root, plan.get("evidence"))
    analysis = {"status": status, "unanalysed": unanalysed, "inputs": inputs, "evidence": evidence}
    index = {feature["id"]: feature for feature in document["features"]}
    for identifier, report in mapping(plan.get("features", {}), "features").items():
        if identifier not in index or index[identifier]["status"] != "active":
            raise ValueError(f"활성 Feature가 아닙니다: {identifier}")
        report = mapping(report, "Feature 분석")
        discovery = mapping(report.get("discovery"), "discovery")
        assessed = assess_discovery(discovery)
        findings = sequence(report.get("dependencies"), "dependencies")
        if not findings:
            raise ValueError("핵심 의존성 위험 평가 근거가 필요합니다")
        for finding in findings:
            nonempty(mapping(finding, "finding").get("evidence"), "dependency evidence")
            if finding.get("assessment") not in ("SAFE", "UNKNOWN", "CONFLICT"):
                raise ValueError("의존성 판정이 잘못되었습니다")
        index[identifier]["discovery"] = {
            "plan": discovery, "verdict": assessed["verdict"],
            "dependencies": findings, "analysis_hash": content_hash(analysis),
            "inputs": inputs, "evidence": evidence, "feature_hash": feature_basis(index[identifier]),
        }
    document["analysis"] = analysis
    if status == "complete":
        for feature in document["features"]:
            if feature["status"] == "active":
                check_feature(root, feature, analysis)
    write_document(root, "features.yaml", document)


def check_feature(root, feature, analysis):
    if feature["status"] != "active":
        raise ValueError(f"폐기 Feature는 개발할 수 없습니다: {feature['id']}")
    report = mapping(feature.get("discovery"), "Feature Discovery 기록")
    if report.get("feature_hash") != feature_basis(feature):
        raise ValueError("Feature 위치·상태·의존관계가 변경됐습니다. Discovery를 재평가하세요")
    if report.get("analysis_hash") != content_hash(analysis):
        raise ValueError("프로젝트 분석 범위가 변경돼 Discovery 근거를 다시 확인해야 합니다")
    if report.get("inputs") != input_files(root, list(report.get("inputs", {}))):
        raise ValueError("Discovery 입력이 변경돼 재평가가 필요합니다")
    if report.get("evidence") != verify_evidence(root, list(report.get("evidence", {}))):
        raise ValueError("Discovery 증거가 변경됐습니다")
    if assess_discovery(report["plan"])["verdict"] != "READY":
        raise ValueError("대상 Feature의 Discovery Gate가 READY가 아닙니다")
    findings = report.get("dependencies")
    if not findings:
        raise ValueError("미분석 영역과 핵심 의존성 위험을 확인해야 합니다")
    check_findings(findings)


def develop_check(root, identifiers):
    validate(root)
    identifiers = sequence(identifiers, "features")
    if not identifiers:
        raise ValueError("개발 대상 Feature를 지정하세요")
    document = read_document(root, "features.yaml")
    analysis = document["analysis"]
    if analysis["status"] == "not_started":
        raise ValueError("프로젝트 초기 분석이 not_started입니다")
    if analysis.get("inputs") != input_files(root, list(analysis.get("inputs", {}))):
        raise ValueError("프로젝트 분석 입력이 변경됐습니다")
    if analysis.get("evidence") != verify_evidence(root, list(analysis.get("evidence", {}))):
        raise ValueError("프로젝트 분석 증거가 변경됐습니다")
    features = {feature["id"]: feature for feature in document["features"]}
    visited = set()
    pending = list(identifiers)
    while pending:
        identifier = pending.pop()
        if identifier in visited:
            continue
        if identifier not in features:
            raise ValueError(f"미등록 Feature: {identifier}")
        visited.add(identifier)
        feature = features[identifier]
        check_feature(root, feature, analysis)
        pending.extend(dependency["feature_id"] for dependency in feature["dependencies"])


def register_feature(root, plan, identifier):
    validate(root)
    document = read_document(root, "features.yaml")
    feature = mapping(plan.get("feature"), "feature")
    path = nonempty(feature.get("spec_path"), "spec_path")
    name = nonempty(feature.get("name"), "name")
    if assess_discovery(plan["discovery"])["verdict"] != "READY":
        raise ValueError("Feature 등록에는 READY가 필요합니다")
    if any(record["id"] == identifier or record["spec_path"] == path for record in document["features"]):
        raise ValueError("기존 Feature 식별자나 경로는 재사용할 수 없습니다")
    # Validate the proposed record before writing the authoritative file.
    from .baseline import validate_features
    record = {"id": identifier, "name": name, "spec_path": path,
              "dependencies": feature.get("dependencies", []), "status": "active"}
    proposed = [*document["features"], record]
    validate_features(root, proposed)
    input_files(root, plan.get("paths"))
    verify_evidence(root, plan.get("evidence"))
    document["features"] = proposed
    write_document(root, "features.yaml", document)
    return identifier
