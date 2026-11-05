"""Host and network checks used by the CloudPulse CLI."""
from __future__ import annotations

import platform
import shutil
import socket
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def check_cpu() -> dict[str, Any]:
    cores = os.cpu_count()
    if sys.platform.startswith("linux") and Path("/proc/stat").exists():
        first = _cpu_times()
        time.sleep(0.1)
        second = _cpu_times()
        total = second[0] - first[0]
        idle = second[1] - first[1]
        usage = round(100 * (total - idle) / total, 1) if total else 0.0
        return {"name": "cpu", "status": "ok", "usage_percent": usage, "logical_cores": cores}
    return {"name": "cpu", "status": "unsupported", "usage_percent": None, "logical_cores": cores, "detail": "CPU utilization is currently implemented for Linux /proc/stat."}


def _cpu_times() -> tuple[int, int]:
    fields = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
    # Linux reports guest time as part of user/nice already; do not count it twice.
    total = sum(fields[:8])
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
    return total, idle


def check_memory() -> dict[str, Any]:
    if sys.platform.startswith("linux") and Path("/proc/meminfo").exists():
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            match = re.match(r"(MemTotal|MemAvailable):\s+(\d+)", line)
            if match: values[match.group(1)] = int(match.group(2)) * 1024
        total, available = values["MemTotal"], values["MemAvailable"]
        percent = round(100 * (total - available) / total, 1)
        return {"name": "memory", "status": "warning" if percent >= 90 else "ok", "usage_percent": percent, "available_bytes": available, "total_bytes": total}
    return {"name": "memory", "status": "unsupported", "detail": "Memory utilization is currently implemented for Linux /proc/meminfo."}


def check_disk(path: str = "/") -> dict[str, Any]:
    d = shutil.disk_usage(path)
    percent = round(100 * d.used / d.total, 1) if d.total else 0.0
    return {"name": "disk", "status": "warning" if percent >= 90 else "ok", "path": path, "usage_percent": percent, "free_bytes": d.free, "total_bytes": d.total}


def check_processes(limit: int = 5) -> dict[str, Any]:
    rows = []
    if sys.platform.startswith("linux") and Path("/proc").exists():
        total_kb = next((int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:")), 1)
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit(): continue
            try:
                name = (proc / "comm").read_text().strip()
                status = (proc / "status").read_text()
                rss = int(re.search(r"^VmRSS:\s+(\d+)", status, re.M).group(1))
                rows.append({"pid": int(proc.name), "name": name, "memory_percent": round(100 * rss / total_kb, 3)})
            except (OSError, AttributeError, ValueError):
                continue
    rows.sort(key=lambda row: row["memory_percent"], reverse=True)
    return {"name": "processes", "status": "ok", "top_by_memory": rows[:limit]}


def check_system() -> dict[str, Any]:
    uptime = None
    if sys.platform.startswith("linux") and Path("/proc/uptime").exists():
        uptime = int(float(Path("/proc/uptime").read_text().split()[0]))
    return {"name": "system", "status": "ok", "platform": platform.platform(), "python": platform.python_version(), "uptime_seconds": uptime}


def check_dns(host: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        records = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
        return {"name": "dns", "target": host, "status": "ok", "addresses": records, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
    except (socket.gaierror, OSError) as exc:
        return {"name": "dns", "target": host, "status": "error", "error": str(exc), "duration_ms": round((time.perf_counter() - started) * 1000, 2)}


def check_tcp(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"name": "tcp", "target": f"{host}:{port}", "status": "ok", "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
    except OSError as exc:
        return {"name": "tcp", "target": f"{host}:{port}", "status": "error", "error": str(exc), "duration_ms": round((time.perf_counter() - started) * 1000, 2)}


def check_http(url: str, timeout: float = 5.0) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"User-Agent": "CloudPulse/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            code = response.status
            return {"name": "http", "target": url, "status": "ok" if 200 <= code < 400 else "error", "http_status": code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
    except urllib.error.HTTPError as exc:
        return {"name": "http", "target": url, "status": "error", "http_status": exc.code, "error": str(exc), "duration_ms": round((time.perf_counter() - started) * 1000, 2)}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"name": "http", "target": url, "status": "error", "error": str(exc), "duration_ms": round((time.perf_counter() - started) * 1000, 2)}


def run_diagnostics(*, dns: str | None = None, tcp: tuple[str, int] | None = None, url: str | None = None, disk_path: str = os.path.abspath(os.sep)) -> dict[str, Any]:
    results = [check_system(), check_cpu(), check_memory(), check_disk(disk_path), check_processes()]
    if dns:
        results.append(check_dns(dns))
    if tcp:
        results.append(check_tcp(*tcp))
    if url:
        results.append(check_http(url))
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "summary": {"total": len(results), "ok": sum(r["status"] == "ok" for r in results), "issues": sum(r["status"] in {"warning", "error"} for r in results), "unsupported": sum(r["status"] == "unsupported" for r in results)}, "checks": results}
