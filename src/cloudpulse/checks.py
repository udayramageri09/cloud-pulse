"""Host and network checks used by the CloudPulse CLI.

Host checks read Linux's /proc filesystem directly (no psutil). The /proc
location is configurable (``proc_root`` argument or ``CLOUDPULSE_PROC_ROOT``)
so the parsers can be tested against fixture files on any operating system.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

from . import __version__

CPU_WARNING_PERCENT = 90
MEMORY_WARNING_PERCENT = 90
DISK_WARNING_PERCENT = 90
TLS_WARNING_DAYS = 14


def proc_root(override: str | os.PathLike[str] | None = None) -> Path:
    """Where to read /proc from: explicit override, then env var, then /proc."""
    return Path(override or os.environ.get("CLOUDPULSE_PROC_ROOT", "/proc"))


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _cpu_times(proc: Path) -> tuple[int, int]:
    """Return (total, idle) jiffies from the aggregate 'cpu' line of /proc/stat."""
    fields = [int(value) for value in (proc / "stat").read_text().splitlines()[0].split()[1:]]
    # Linux already counts guest time inside user/nice, so only the first 8 fields are summed.
    total = sum(fields[:8])
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)  # idle + iowait
    return total, idle


def check_cpu(
    proc: Path | None = None, sample_seconds: float = 0.1, warn_percent: float | None = None
) -> dict[str, Any]:
    proc = proc_root(proc)
    cores = os.cpu_count()
    if not (proc / "stat").exists():
        return {
            "name": "cpu",
            "status": "unsupported",
            "usage_percent": None,
            "logical_cores": cores,
            "detail": "CPU utilization is read from /proc/stat (Linux only).",
        }
    # /proc/stat counters are cumulative since boot, so utilization needs two samples.
    first = _cpu_times(proc)
    time.sleep(sample_seconds)
    second = _cpu_times(proc)
    total = second[0] - first[0]
    idle = second[1] - first[1]
    usage = round(100 * (total - idle) / total, 1) if total else 0.0
    status = "warning" if usage >= (warn_percent or CPU_WARNING_PERCENT) else "ok"
    return {"name": "cpu", "status": status, "usage_percent": usage, "logical_cores": cores}


def check_load(proc: Path | None = None, cores: int | None = None) -> dict[str, Any]:
    """1/5/15-minute load averages; warn when runnable tasks exceed the CPU count."""
    proc = proc_root(proc)
    cores = cores or os.cpu_count() or 1
    if not (proc / "loadavg").exists():
        return {
            "name": "load",
            "status": "unsupported",
            "detail": "Load average is read from /proc/loadavg (Linux only).",
        }
    one, five, fifteen = (float(v) for v in (proc / "loadavg").read_text().split()[:3])
    per_core = round(one / cores, 2)
    # Load counts runnable (and uninterruptible) tasks; above 1.0 per core means work is queueing.
    status = "warning" if per_core >= 1.0 else "ok"
    return {
        "name": "load",
        "status": status,
        "load_1m": one,
        "load_5m": five,
        "load_15m": fifteen,
        "per_core_1m": per_core,
        "logical_cores": cores,
    }


def _meminfo(proc: Path) -> dict[str, int]:
    """Parse /proc/meminfo into bytes."""
    values = {}
    for line in (proc / "meminfo").read_text().splitlines():
        match = re.match(r"(\w+):\s+(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    return values


def check_memory(proc: Path | None = None, warn_percent: float | None = None) -> dict[str, Any]:
    proc = proc_root(proc)
    if not (proc / "meminfo").exists():
        return {
            "name": "memory",
            "status": "unsupported",
            "detail": "Memory utilization is read from /proc/meminfo (Linux only).",
        }
    values = _meminfo(proc)
    total, available = values["MemTotal"], values["MemAvailable"]
    percent = round(100 * (total - available) / total, 1)
    status = "warning" if percent >= (warn_percent or MEMORY_WARNING_PERCENT) else "ok"
    return {
        "name": "memory",
        "status": status,
        "usage_percent": percent,
        "available_bytes": available,
        "total_bytes": total,
    }


def check_disk(path: str = "/", warn_percent: float | None = None) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        return {"name": "disk", "status": "error", "path": path, "error": str(exc)}
    percent = round(100 * usage.used / usage.total, 1) if usage.total else 0.0
    status = "warning" if percent >= (warn_percent or DISK_WARNING_PERCENT) else "ok"
    return {
        "name": "disk",
        "status": status,
        "path": path,
        "usage_percent": percent,
        "free_bytes": usage.free,
        "total_bytes": usage.total,
    }


def check_processes(proc: Path | None = None, limit: int = 5) -> dict[str, Any]:
    proc = proc_root(proc)
    rows = []
    if (proc / "meminfo").exists():
        total_kb = _meminfo(proc)["MemTotal"] // 1024 or 1
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                name = (entry / "comm").read_text().strip()
                rss = re.search(r"^VmRSS:\s+(\d+)", (entry / "status").read_text(), re.M)
                if rss is None:  # kernel threads have no resident memory
                    continue
                rows.append(
                    {
                        "pid": int(entry.name),
                        "name": name,
                        "memory_percent": round(100 * int(rss.group(1)) / total_kb, 3),
                    }
                )
            except (OSError, ValueError):
                continue  # the process exited between listing and reading it
    rows.sort(key=lambda row: row["memory_percent"], reverse=True)
    return {"name": "processes", "status": "ok", "scanned": len(rows), "top_by_memory": rows[:limit]}


def check_system(proc: Path | None = None) -> dict[str, Any]:
    proc = proc_root(proc)
    uptime = None
    if (proc / "uptime").exists():
        uptime = int(float((proc / "uptime").read_text().split()[0]))
    return {
        "name": "system",
        "status": "ok",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "uptime_seconds": uptime,
    }


def check_dns(host: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        records = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
        return {
            "name": "dns",
            "target": host,
            "status": "ok",
            "addresses": records,
            "duration_ms": _elapsed_ms(started),
        }
    except OSError as exc:  # socket.gaierror is a subclass of OSError
        return {
            "name": "dns",
            "target": host,
            "status": "error",
            "error": str(exc),
            "duration_ms": _elapsed_ms(started),
        }


def check_tcp(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    started = time.perf_counter()
    target = f"{host}:{port}"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"name": "tcp", "target": target, "status": "ok", "duration_ms": _elapsed_ms(started)}
    except OSError as exc:
        return {
            "name": "tcp",
            "target": target,
            "status": "error",
            "error": str(exc),
            "duration_ms": _elapsed_ms(started),
        }


def check_http(url: str, timeout: float = 5.0) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"User-Agent": f"CloudPulse/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            code = response.status
            return {
                "name": "http",
                "target": url,
                "status": "ok" if 200 <= code < 400 else "error",
                "http_status": code,
                "duration_ms": _elapsed_ms(started),
            }
    except urllib.error.HTTPError as exc:
        return {
            "name": "http",
            "target": url,
            "status": "error",
            "http_status": exc.code,
            "error": str(exc),
            "duration_ms": _elapsed_ms(started),
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "name": "http",
            "target": url,
            "status": "error",
            "error": str(exc),
            "duration_ms": _elapsed_ms(started),
        }


def _peer_cert_not_after(host: str, port: int, timeout: float, cafile: str | None) -> datetime:
    """TLS handshake with full verification; return the leaf certificate's expiry time."""
    context = ssl.create_default_context(cafile=cafile)
    with (
        socket.create_connection((host, port), timeout=timeout) as sock,
        context.wrap_socket(sock, server_hostname=host) as tls,
    ):
        cert = tls.getpeercert()
    return datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), tz=timezone.utc)


def check_tls(
    host: str,
    port: int = 443,
    timeout: float = 5.0,
    cafile: str | None = None,
    now: datetime | None = None,
    warn_days: int | None = None,
) -> dict[str, Any]:
    """Verify the certificate chain and hostname, and report days until the certificate expires."""
    started = time.perf_counter()
    target = f"{host}:{port}"
    try:
        not_after = _peer_cert_not_after(host, port, timeout, cafile)
    except ssl.SSLCertVerificationError as exc:  # expired, self-signed, wrong hostname...
        return {
            "name": "tls",
            "target": target,
            "status": "error",
            "error": f"certificate verification failed: {exc.verify_message}",
            "duration_ms": _elapsed_ms(started),
        }
    except OSError as exc:  # refused, timeout, handshake failure (ssl.SSLError is an OSError)
        return {
            "name": "tls",
            "target": target,
            "status": "error",
            "error": str(exc),
            "duration_ms": _elapsed_ms(started),
        }
    days = int((not_after - (now or datetime.now(timezone.utc))).total_seconds() // 86400)
    status = "warning" if days < (warn_days or TLS_WARNING_DAYS) else "ok"
    return {
        "name": "tls",
        "target": target,
        "status": status,
        "expires_at": not_after.isoformat(),
        "days_remaining": days,
        "duration_ms": _elapsed_ms(started),
    }


def run_diagnostics(
    *,
    dns: str | None = None,
    tcp: tuple[str, int] | None = None,
    url: str | None = None,
    disk_path: str = os.path.abspath(os.sep),
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run all host checks plus the requested network checks.

    ``thresholds`` may override ``cpu``, ``memory``, ``disk`` (percent) and ``tls_days``.
    """
    limits = thresholds or {}
    results = [
        check_system(),
        check_cpu(warn_percent=limits.get("cpu")),
        check_load(),
        check_memory(warn_percent=limits.get("memory")),
        check_disk(disk_path, warn_percent=limits.get("disk")),
        check_processes(),
    ]

    network = []  # zero-argument callables, in report order
    if dns:
        network.append(partial(check_dns, dns))
    if tcp:
        network.append(partial(check_tcp, *tcp))
    if url:
        network.append(partial(check_http, url))
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname:
            network.append(partial(check_tls, parsed.hostname, parsed.port or 443, warn_days=limits.get("tls_days")))
    if network:
        # Network checks spend their time waiting on I/O, so run them concurrently:
        # total time is the slowest check, not the sum. map() keeps the report order.
        with ThreadPoolExecutor(max_workers=len(network)) as pool:
            results.extend(pool.map(lambda job: job(), network))
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "checks": results}
