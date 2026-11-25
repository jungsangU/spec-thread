from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from specthread_monitor.metrics import REPORT, dashboard, test_report


class DashboardMetricsTest(unittest.TestCase):
    def test_report_counts_failures_errors_and_skips_once(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(test_report(root)["state"], "missing")
            path = root / REPORT
            path.parent.mkdir()
            path.write_text("""<testsuites><testsuite tests="4"><testcase/>
                <testcase><failure/></testcase><testsuite><testcase><error/></testcase>
                <testcase><skipped/></testcase></testsuite></testsuite></testsuites>""")
            report = test_report(root)
            self.assertEqual([report[k] for k in ("passed", "failed", "errors", "skipped")], [1, 1, 1, 1])
            path.write_text('<!DOCTYPE testsuite [<!ENTITY x "data">]><testsuite>&x;</testsuite>')
            self.assertEqual(test_report(root)["state"], "unavailable")

    def test_dashboard_counts_only_active_tasks_and_current_required_pass(self):
        baseline = {
            "features": [{"status": "active", "tasks": {"done": 2, "total": 3}},
                         {"status": "retired", "tasks": {"done": 1, "total": 1}}],
            "items": [{"status": "completed", "gates": [{"required": True, "current": None}]},
                      {"status": "pending", "gates": []},
                      {"status": "in_progress", "gates": [{"required": True, "current": "STALE"},
                                                          {"required": True, "current": "PASS"},
                                                          {"required": False, "current": "PASS"}]}],
        }
        data = dashboard(baseline, {"state": "missing"})
        self.assertEqual((data["tasks_done"], data["tasks_total"]), (2, 3))
        self.assertEqual((data["work_completed"], data["work_total"]), (1, 3))
        self.assertEqual((data["required_pass"], data["required_total"], data["items_without_gates"]), (1, 3, 1))

    def test_completed_gate_remains_in_project_progress(self):
        item = {"status": "in_progress", "gates": [{"required": True, "current": "PASS", "recorded": "PASS"}]}
        baseline = {"features": [], "items": [item]}
        before = dashboard(baseline, {"state": "missing"})
        item.update(status="completed")
        item['gates'][0]['current'] = None
        after = dashboard(baseline, {"state": "missing"})
        self.assertEqual(before['required_total'], after['required_total'])
        self.assertEqual(after['required_pass'] + after['historical_pass'], 1)
        self.assertEqual(after['work_completed'], 1)
