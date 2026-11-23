"""Dashboard totals derived from the visible Baseline and a local JUnit report."""
from datetime import datetime, timezone
from xml.etree import ElementTree

from .observe import project_path, safe_file

REPORT = "test-results/junit.xml"
LIMIT = 2 * 1024 * 1024


def test_report(root):
    try:
        path = safe_file(project_path(root, REPORT), LIMIT)
        if not path.is_file():
            return {"state": "missing", "path": REPORT}
        with path.open("rb") as report:
            contents = report.read(LIMIT + 1)
        xml = contents.decode("utf-8-sig")
        if len(contents) > LIMIT or "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
            raise ValueError("Unsupported report")
        tree = ElementTree.fromstring(xml)
        if tree.tag not in ("testsuites", "testsuite"):
            raise ValueError("Unsupported report")
        outcomes = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        for case in tree.iter("testcase"):
            outcome = "passed"
            for tag, name in (("error", "errors"), ("failure", "failed"), ("skipped", "skipped")):
                if case.find(tag) is not None:
                    outcome = name
                    break
            outcomes[outcome] += 1
        return {"state": "available", "path": REPORT, **outcomes,
                "reported_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
    except (OSError, ValueError, ElementTree.ParseError):
        return {"state": "unavailable", "path": REPORT}


def dashboard(baseline, tests):
    features = [row for row in baseline.get("features", []) if row["status"] == "active"]
    works = baseline.get("items", [])
    open_work = [row for row in works if row["status"] not in ("completed", "failed")]
    gates = [gate for row in open_work for gate in row["gates"] if gate["required"]]
    return {
        "tasks_done": sum(row["tasks"]["done"] for row in features if row["tasks"]),
        "tasks_total": sum(row["tasks"]["total"] for row in features if row["tasks"]),
        "features_with_tasks": sum(bool(row["tasks"]) for row in features),
        "active_features": len(features),
        "feature_sampled": baseline.get("feature_count", 0) > len(baseline.get("features", [])),
        "work_completed": sum(row["status"] == "completed" for row in works),
        "work_total": len(works),
        "work_sampled": baseline.get("item_count", 0) > len(works),
        "required_pass": sum(gate["current"] == "PASS" for gate in gates),
        "required_total": len(gates),
        "items_without_gates": sum(not any(gate["required"] for gate in row["gates"]) for row in open_work),
        "tests": tests,
    }
