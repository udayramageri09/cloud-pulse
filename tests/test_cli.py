"""CLI behaviour: exit codes, argument validation and threshold plumbing."""

import json

import pytest

from cloudpulse import cli


def fake_report(*statuses):
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "checks": [{"name": f"c{i}", "status": s} for i, s in enumerate(statuses)],
    }


@pytest.mark.parametrize(
    "statuses, code",
    [
        (("ok", "ok"), 0),
        (("ok", "warning"), 1),
        (("warning", "error"), 2),
    ],
)
def test_exit_code_follows_overall_status(monkeypatch, statuses, code, capsys):
    monkeypatch.setattr(cli, "run_diagnostics", lambda **_: fake_report(*statuses))
    assert cli.main([]) == code


@pytest.mark.parametrize(
    "argv", [["--tcp", "nohost"], ["--tcp", "h:70000"], ["--url", "ftp://x"], ["--cpu-warn", "150"]]
)
def test_bad_arguments_exit_3_not_2(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 3  # 2 would be read as "critical" by monitoring systems
    assert "error:" in capsys.readouterr().err


def test_thresholds_are_passed_through(monkeypatch):
    seen = {}

    def capture(**kwargs):
        seen.update(kwargs)
        return fake_report("ok")

    monkeypatch.setattr(cli, "run_diagnostics", capture)
    cli.main(["--cpu-warn", "75", "--disk-warn", "80", "--tls-warn-days", "30"])
    assert seen["thresholds"] == {"cpu": 75.0, "disk": 80.0, "tls_days": 30}


def test_json_report_written_to_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "run_diagnostics", lambda **_: fake_report("ok"))
    out = tmp_path / "reports" / "incident.json"
    assert cli.main(["--format", "json", "--output", str(out)]) == 0
    assert json.loads(out.read_text())["overall_status"] == "healthy"
