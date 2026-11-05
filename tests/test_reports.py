import json
import unittest

from cloudpulse.report import build_incident, classify, to_json, to_text


class ClassifyTests(unittest.TestCase):
    def test_ok_check_has_info_severity_and_no_symptom(self):
        enriched = classify({"name": "disk", "status": "ok", "usage_percent": 10.0, "path": "/"})
        self.assertEqual(enriched["severity"], "info")
        self.assertNotIn("symptom", enriched)
        self.assertNotIn("next_steps", enriched)

    def test_warning_check_gets_symptom_and_next_steps(self):
        enriched = classify({"name": "memory", "status": "warning", "usage_percent": 95.0})
        self.assertEqual(enriched["severity"], "warning")
        self.assertIn("95.0%", enriched["symptom"])
        self.assertTrue(enriched["next_steps"])

    def test_error_check_is_critical(self):
        enriched = classify({"name": "dns", "status": "error", "target": "bad.invalid", "error": "not found"})
        self.assertEqual(enriched["severity"], "critical")
        self.assertIn("bad.invalid", enriched["symptom"])

    def test_unsupported_check_is_info_with_detail_symptom(self):
        enriched = classify({"name": "cpu", "status": "unsupported", "detail": "Linux only."})
        self.assertEqual(enriched["severity"], "info")
        self.assertEqual(enriched["symptom"], "Linux only.")


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.raw_report = {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "checks": [
                {"name": "cpu", "status": "ok", "usage_percent": 2.0, "logical_cores": 8},
                {"name": "dns", "target": "bad.invalid", "status": "error", "error": "not found"},
            ],
        }

    def test_build_incident_assigns_id_host_and_overall_status(self):
        incident = build_incident(self.raw_report)
        self.assertTrue(incident["incident_id"].startswith("CP-"))
        self.assertIn("hostname", incident["host"])
        self.assertEqual(incident["overall_status"], "critical")
        self.assertEqual(incident["summary"], {"total": 2, "info": 1, "warning": 0, "critical": 1})

    def test_json_is_valid_and_preserves_check_results(self):
        incident = build_incident(self.raw_report)
        parsed = json.loads(to_json(incident))
        self.assertEqual(parsed["overall_status"], "critical")
        self.assertEqual(len(parsed["checks"]), 2)

    def test_text_includes_summary_and_failure_symptom(self):
        rendered = to_text(build_incident(self.raw_report))
        self.assertIn("Overall status: CRITICAL", rendered)
        self.assertIn("[CRITICAL] dns (bad.invalid)", rendered)
        self.assertIn("Symptom: dns (bad.invalid) failed: not found", rendered)

    def test_verbose_shows_info_level_symptoms_too(self):
        raw = {"generated_at": "x", "checks": [{"name": "cpu", "status": "unsupported", "detail": "Linux only."}]}
        quiet = to_text(build_incident(raw), verbose=False)
        verbose = to_text(build_incident(raw), verbose=True)
        self.assertNotIn("Symptom:", quiet)
        self.assertIn("Symptom: Linux only.", verbose)


if __name__ == "__main__":
    unittest.main()
