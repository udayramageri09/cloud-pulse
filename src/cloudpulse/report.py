"""Incident report assembly and rendering.

`checks.py` reports observed facts (status, measured values). This module
classifies those facts into severities and suggests investigation next steps.
It never asserts a root cause -- only what was observed and what to look at next.
"""
from __future__ import annotations

import json
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Any

_SEVERITY_BY_STATUS = {"ok": "info", "unsupported": "info", "warning": "warning", "error": "critical"}

_NEXT_STEPS: dict[str, list[str]] = {
    "cpu": [
        "Take a second reading to see whether load is sustained or a brief spike",
        "Check the process list in this report for the busiest processes before restarting anything",
    ],
    "memory": [
        "Inspect the top-memory process list in this report",
        "Distinguish a steadily growing process (a leak) from generally high but stable usage",
    ],
    "disk": [
        "Run `du` on the affected path to find what is consuming space",
        "Preserve logs/evidence before deleting anything",
    ],
    "dns": [
        "Confirm the hostname spelling and try a second resolver, e.g. `getent hosts <name>`",
        "If only this host is affected, check its local resolver configuration",
    ],
    "tcp": [
        "Confirm the host and port, and check for a firewall or security group blocking it",
        "Verify the service is actually listening on that interface (`ss -tln` on the target)",
    ],
    "http": [
        "Compare with the TCP result: a reachable port with a failing HTTP response points at the application or proxy, not the network path",
        "Inspect application/proxy logs to distinguish a gateway error from an application error",
    ],
}


def _symptom(check: dict[str, Any]) -> str | None:
    name, status = check["name"], check["status"]
    if status == "warning":
        if name == "cpu":
            return f"CPU utilization at {check['usage_percent']}% across {check['logical_cores']} logical cores"
        if name == "memory":
            return f"Memory usage at {check['usage_percent']}%"
        if name == "disk":
            return f"Disk usage at {check['usage_percent']}% on {check['path']}"
    if status == "error":
        target = f" ({check['target']})" if check.get("target") else ""
        return f"{name}{target} failed: {check.get('error', 'see error field')}"
    if status == "unsupported":
        return check.get("detail", f"{name} is not supported on this platform")
    return None


def classify(check: dict[str, Any]) -> dict[str, Any]:
    """Attach severity and, for anything noteworthy, a symptom and next steps."""
    enriched = dict(check)
    severity = _SEVERITY_BY_STATUS.get(check["status"], "info")
    enriched["severity"] = severity
    symptom = _symptom(check)
    if symptom:
        enriched["symptom"] = symptom
    if severity in {"warning", "critical"}:
        enriched["next_steps"] = _NEXT_STEPS.get(check["name"], [])
    return enriched


def _overall_status(checks: list[dict[str, Any]]) -> str:
    severities = {c["severity"] for c in checks}
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "degraded"
    return "healthy"


def build_incident(raw_report: dict[str, Any]) -> dict[str, Any]:
    """Turn a raw `run_diagnostics()` result into a full incident report."""
    checks = [classify(c) for c in raw_report["checks"]]
    counts = {"info": 0, "warning": 0, "critical": 0}
    for c in checks:
        counts[c["severity"]] += 1
    now = datetime.now(timezone.utc)
    return {
        "incident_id": f"CP-{now:%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}",
        "generated_at": raw_report["generated_at"],
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        },
        "overall_status": _overall_status(checks),
        "summary": {"total": len(checks), **counts},
        "checks": checks,
    }


def to_json(incident: dict[str, Any]) -> str:
    return json.dumps(incident, indent=2, sort_keys=True)


_HIDDEN_DETAIL_KEYS = {"name", "status", "target", "severity", "symptom", "next_steps"}


def to_text(incident: dict[str, Any], verbose: bool = False) -> str:
    host, summary = incident["host"], incident["summary"]
    lines = [
        "CloudPulse Incident Report",
        f"Incident ID: {incident['incident_id']}",
        f"Generated: {incident['generated_at']}",
        f"Host: {host['hostname']} ({host['platform']}, Python {host['python_version']})",
        f"Overall status: {incident['overall_status'].upper()}",
        f"Checks: {summary['total']} total - {summary['info']} info, {summary['warning']} warning, {summary['critical']} critical",
        "",
    ]
    for check in incident["checks"]:
        target = f" ({check['target']})" if check.get("target") else ""
        details = ", ".join(f"{k}={v}" for k, v in check.items() if k not in _HIDDEN_DETAIL_KEYS)
        lines.append(f"[{check['severity'].upper()}] {check['name']}{target}" + (f" - {details}" if details else ""))
        show_extra = verbose or check["severity"] in {"warning", "critical"}
        if show_extra and check.get("symptom"):
            lines.append(f"    Symptom: {check['symptom']}")
        for step in check.get("next_steps", []) if show_extra else []:
            lines.append(f"    Next step: {step}")
    return "\n".join(lines)
