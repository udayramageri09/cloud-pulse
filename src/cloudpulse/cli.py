"""Command line interface."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .checks import run_diagnostics
from .report import build_incident, to_json, to_text

# Nagios/Icinga plugin convention, so CloudPulse can drop into existing monitoring.
EXIT_CODES = {"healthy": 0, "degraded": 1, "critical": 2}
EXIT_USAGE = 3  # "UNKNOWN": the check could not run as asked

EPILOG = """exit status (Nagios plugin convention):
  0  healthy   every check passed
  1  degraded  at least one warning
  2  critical  at least one failed check
  3  unknown   invalid arguments
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would exit 2, which means "critical" here
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def _percent(value: str) -> float:
    number = float(value)
    if not 0 < number <= 100:
        raise argparse.ArgumentTypeError("must be between 0 and 100")
    return number


def _days(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="cloudpulse", description="Collect host and network diagnostics for incident triage.",
                epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dns", metavar="HOST", help="resolve a DNS hostname")
    p.add_argument("--tcp", metavar="HOST:PORT", help="test a TCP connection")
    p.add_argument("--url", help="check an HTTP or HTTPS endpoint; https also checks the TLS certificate")
    p.add_argument("--disk-path", default=os.path.abspath(os.sep), help="filesystem path to inspect (default: system root)")
    p.add_argument("--cpu-warn", type=_percent, metavar="PCT", help="CPU usage warning threshold (default 90)")
    p.add_argument("--mem-warn", type=_percent, metavar="PCT", help="memory usage warning threshold (default 90)")
    p.add_argument("--disk-warn", type=_percent, metavar="PCT", help="disk usage warning threshold (default 90)")
    p.add_argument("--tls-warn-days", type=_days, metavar="DAYS", help="warn when the certificate expires sooner (default 14)")
    p.add_argument("--format", choices=("text", "json"), default="text", help="report format")
    p.add_argument("--output", type=Path, help="write report to this file instead of stdout")
    p.add_argument("--verbose", action="store_true",
                   help="show symptoms and next steps for every check, not just warnings/errors (text format only)")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    tcp = None
    if args.tcp:
        try:
            host, raw_port = args.tcp.rsplit(":", 1)
            port = int(raw_port)
            if not host or not 1 <= port <= 65535:
                raise ValueError
            tcp = (host, port)
        except ValueError:
            parser.error("--tcp must be HOST:PORT with a port from 1 to 65535")
    if args.url and not args.url.startswith(("http://", "https://")):
        parser.error("--url must start with http:// or https://")
    thresholds = {key: value for key, value in {
        "cpu": args.cpu_warn, "memory": args.mem_warn, "disk": args.disk_warn, "tls_days": args.tls_warn_days,
    }.items() if value is not None}
    raw_report = run_diagnostics(dns=args.dns, tcp=tcp, url=args.url, disk_path=args.disk_path, thresholds=thresholds)
    incident = build_incident(raw_report)
    rendered = to_json(incident) if args.format == "json" else to_text(incident, verbose=args.verbose)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return EXIT_CODES[incident["overall_status"]]


if __name__ == "__main__":
    sys.exit(main())
