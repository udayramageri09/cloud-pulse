import unittest
from unittest.mock import patch

from cloudpulse.checks import check_cpu, check_disk, check_dns, check_tcp, run_diagnostics


class ChecksTests(unittest.TestCase):
    def test_dns_returns_error_for_unresolvable_host(self):
        with patch("cloudpulse.checks.socket.getaddrinfo", side_effect=OSError("no such host")):
            self.assertEqual(check_dns("bad.invalid")["status"], "error")

    def test_tcp_returns_error_when_connection_fails(self):
        with patch("cloudpulse.checks.socket.create_connection", side_effect=OSError("refused")):
            self.assertEqual(check_tcp("localhost", 80)["status"], "error")

    def test_disk_returns_error_for_nonexistent_path(self):
        with patch("cloudpulse.checks.shutil.disk_usage", side_effect=OSError("no such path")):
            result = check_disk("/does/not/exist")
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_cpu_flags_warning_at_or_above_threshold(self):
        with patch("cloudpulse.checks.sys.platform", "linux"), \
             patch("cloudpulse.checks.Path.exists", return_value=True), \
             patch("cloudpulse.checks._cpu_times", side_effect=[(1000, 0), (2000, 50)]):
            result = check_cpu()
        self.assertEqual(result["status"], "warning")
        self.assertGreaterEqual(result["usage_percent"], 90)

    def test_run_diagnostics_includes_requested_network_checks(self):
        with patch("cloudpulse.checks.check_dns", return_value={"name": "dns", "status": "ok"}), patch("cloudpulse.checks.check_tcp", return_value={"name": "tcp", "status": "ok"}), patch("cloudpulse.checks.check_http", return_value={"name": "http", "status": "ok"}):
            report = run_diagnostics(dns="example.com", tcp=("example.com", 443), url="https://example.com", disk_path="/")
        self.assertEqual([r["name"] for r in report["checks"]][-3:], ["dns", "tcp", "http"])


if __name__ == "__main__":
    unittest.main()
