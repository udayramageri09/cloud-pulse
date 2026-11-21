"""Parser tests against a fake /proc tree, so they run on any OS."""
from pathlib import Path

from cloudpulse import checks

FIXTURE = Path(__file__).parent / "fixtures" / "proc"


def test_memory_uses_memavailable_not_memfree():
    result = checks.check_memory(FIXTURE)
    # used = total - available = 8,000,000 - 2,000,000 kB -> 75%
    assert result["status"] == "ok"
    assert result["usage_percent"] == 75.0
    assert result["total_bytes"] == 8_000_000 * 1024


def test_cpu_usage_comes_from_the_delta_of_two_samples(tmp_path, monkeypatch):
    stat = tmp_path / "stat"
    stat.write_text("cpu  100 0 100 800 0 0 0 0 0 0\n")

    def advance_counters(_seconds):
        # Between samples: 300 busy + 100 idle jiffies -> 75% busy.
        stat.write_text("cpu  300 0 200 900 0 0 0 0 0 0\n")

    monkeypatch.setattr(checks.time, "sleep", advance_counters)
    result = checks.check_cpu(tmp_path)
    assert result["usage_percent"] == 75.0
    assert result["status"] == "ok"


def test_cpu_counts_iowait_as_idle(tmp_path, monkeypatch):
    stat = tmp_path / "stat"
    stat.write_text("cpu  0 0 0 0 0 0 0 0\n")
    monkeypatch.setattr(checks.time, "sleep",
                        lambda _s: stat.write_text("cpu  50 0 0 25 25 0 0 0\n"))
    assert checks.check_cpu(tmp_path)["usage_percent"] == 50.0


def test_processes_sorted_by_memory_and_kernel_threads_skipped():
    result = checks.check_processes(FIXTURE)
    names = [row["name"] for row in result["top_by_memory"]]
    assert names == ["postgres", "systemd"]  # kthreadd has no VmRSS
    assert result["scanned"] == 2
    assert result["top_by_memory"][0]["memory_percent"] == 10.0


def test_uptime_is_whole_seconds():
    assert checks.check_system(FIXTURE)["uptime_seconds"] == 35290


def test_missing_proc_is_reported_as_unsupported(tmp_path):
    assert checks.check_cpu(tmp_path)["status"] == "unsupported"
    assert checks.check_memory(tmp_path)["status"] == "unsupported"
    assert checks.check_processes(tmp_path)["scanned"] == 0


def test_env_var_overrides_proc_location(monkeypatch):
    monkeypatch.setenv("CLOUDPULSE_PROC_ROOT", str(FIXTURE))
    assert checks.check_memory()["usage_percent"] == 75.0


def test_load_is_ok_below_one_task_per_core():
    result = checks.check_load(FIXTURE, cores=4)
    assert (result["load_1m"], result["load_5m"], result["load_15m"]) == (0.52, 0.58, 0.59)
    assert result["per_core_1m"] == 0.13
    assert result["status"] == "ok"


def test_load_warns_when_tasks_queue_beyond_core_count(tmp_path):
    (tmp_path / "loadavg").write_text("6.10 3.00 1.50 9/600 4242\n")
    result = checks.check_load(tmp_path, cores=4)
    assert result["status"] == "warning"
    assert result["per_core_1m"] == 1.52


def test_custom_threshold_turns_usage_into_a_warning():
    assert checks.check_memory(FIXTURE, warn_percent=70)["status"] == "warning"
