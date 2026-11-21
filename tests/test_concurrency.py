"""Network checks run concurrently but are reported in a fixed order."""
import time

from cloudpulse import checks


def slow(name, delay):
    def check(*_args, **_kwargs):
        time.sleep(delay)
        return {"name": name, "status": "ok"}
    return check


def test_network_checks_overlap_and_keep_report_order(monkeypatch):
    monkeypatch.setattr(checks, "check_dns", slow("dns", 0.3))
    monkeypatch.setattr(checks, "check_tcp", slow("tcp", 0.3))
    monkeypatch.setattr(checks, "check_http", slow("http", 0.1))  # finishes first
    monkeypatch.setattr(checks, "check_tls", slow("tls", 0.3))
    monkeypatch.setattr(checks, "check_cpu", lambda **_: {"name": "cpu", "status": "ok"})

    started = time.perf_counter()
    report = checks.run_diagnostics(dns="a.test", tcp=("a.test", 443), url="https://a.test")
    elapsed = time.perf_counter() - started

    assert [c["name"] for c in report["checks"]][-4:] == ["dns", "tcp", "http", "tls"]
    assert elapsed < 0.6, f"checks ran sequentially ({elapsed:.2f}s for 1.0s of total work)"
