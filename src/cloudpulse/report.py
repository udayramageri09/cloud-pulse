"""Human-readable incident report rendering."""
import json


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def to_text(report: dict) -> str:
    unsupported = report["summary"].get("unsupported", 0)
    lines = ["CloudPulse Incident Report", f"Generated: {report['generated_at']}", f"Checks: {report['summary']['ok']} ok, {report['summary']['issues']} issue(s), {unsupported} unsupported", ""]
    for check in report["checks"]:
        status = check["status"].upper()
        target = f" ({check['target']})" if check.get("target") else ""
        details = ", ".join(f"{k}={v}" for k, v in check.items() if k not in {"name", "status", "target"})
        lines.append(f"[{status}] {check['name']}{target}" + (f" — {details}" if details else ""))
    return "\n".join(lines)
