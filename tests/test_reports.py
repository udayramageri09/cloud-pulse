import json
import unittest

from cloudpulse.report import to_json, to_text


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {"generated_at": "2026-01-01T00:00:00+00:00", "summary": {"total": 2, "ok": 1, "issues": 1, "unsupported": 0}, "checks": [{"name": "cpu", "status": "ok", "usage_percent": 2.0}, {"name": "dns", "target": "bad.invalid", "status": "error", "error": "not found"}]}

    def test_json_is_valid_and_preserves_results(self):
        self.assertEqual(json.loads(to_json(self.report)), self.report)

    def test_text_includes_summary_and_failure(self):
        rendered = to_text(self.report)
        self.assertIn("1 ok, 1 issue(s), 0 unsupported", rendered)
        self.assertIn("[ERROR] dns (bad.invalid)", rendered)
