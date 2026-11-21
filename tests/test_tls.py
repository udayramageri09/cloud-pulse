"""TLS checks against a real local TLS server with throwaway certificates."""

import shutil
import socket
import ssl
import subprocess
import threading
from datetime import datetime, timedelta, timezone

import pytest

from cloudpulse import checks
from cloudpulse.report import classify

pytestmark = pytest.mark.skipif(shutil.which("openssl") is None, reason="needs the openssl CLI")


def make_cert(tmp_path, days):
    key, cert = tmp_path / f"key{days}.pem", tmp_path / f"cert{days}.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            str(days),
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        check=True,
        capture_output=True,
    )
    return cert, key


@pytest.fixture
def tls_server(tmp_path):
    """Start a one-connection-at-a-time TLS server; yields a function (days) -> (port, cafile)."""
    servers = []

    def start(days):
        cert, key = make_cert(tmp_path, days)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert, key)
        listener = socket.create_server(("127.0.0.1", 0))
        servers.append(listener)

        def serve():
            while True:
                try:
                    conn, _ = listener.accept()
                except OSError:
                    return
                try:
                    with context.wrap_socket(conn, server_side=True):
                        pass
                except (ssl.SSLError, OSError):
                    pass  # client rejected our certificate - expected in the negative test

        threading.Thread(target=serve, daemon=True).start()
        return listener.getsockname()[1], str(cert)

    yield start
    for listener in servers:
        listener.close()


def test_valid_certificate_reports_days_remaining(tls_server):
    port, cafile = tls_server(days=90)
    result = checks.check_tls("localhost", port, cafile=cafile)
    assert result["status"] == "ok"
    assert 88 <= result["days_remaining"] <= 90


def test_certificate_close_to_expiry_is_a_warning(tls_server):
    port, cafile = tls_server(days=5)
    result = checks.check_tls("localhost", port, cafile=cafile)
    assert result["status"] == "warning"
    assert "expires in" in classify(result)["symptom"]


def test_untrusted_certificate_fails_verification(tls_server):
    port, _ = tls_server(days=90)
    result = checks.check_tls("localhost", port)  # system CAs do not trust our self-signed cert
    assert result["status"] == "error"
    assert "certificate verification failed" in result["error"]


def test_expiry_maths_uses_whole_days(monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(checks, "_peer_cert_not_after", lambda *a: now + timedelta(days=20, hours=23))
    assert checks.check_tls("example.test", now=now)["days_remaining"] == 20


def test_https_url_adds_a_tls_check(monkeypatch):
    monkeypatch.setattr(checks, "check_http", lambda url: {"name": "http", "status": "ok"})
    monkeypatch.setattr(
        checks, "check_tls", lambda host, port, **_: {"name": "tls", "status": "ok", "target": f"{host}:{port}"}
    )
    names = [c["name"] for c in checks.run_diagnostics(url="https://example.test:8443/x")["checks"]]
    assert names[-2:] == ["http", "tls"]
