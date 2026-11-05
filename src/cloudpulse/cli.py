"""Command line interface."""
import argparse
import os
from pathlib import Path
import sys

from .checks import run_diagnostics
from .report import to_json, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cloudpulse", description="Collect host and network diagnostics for incident triage.")
    p.add_argument("--dns", metavar="HOST", help="resolve a DNS hostname")
    p.add_argument("--tcp", metavar="HOST:PORT", help="test a TCP connection")
    p.add_argument("--url", help="check an HTTP or HTTPS endpoint")
    p.add_argument("--disk-path", default=os.path.abspath(os.sep), help="filesystem path to inspect (default: system root)")
    p.add_argument("--format", choices=("text", "json"), default="text", help="report format")
    p.add_argument("--output", type=Path, help="write report to this file instead of stdout")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tcp = None
    if args.tcp:
        try:
            host, raw_port = args.tcp.rsplit(":", 1)
            port = int(raw_port)
            if not host or not 1 <= port <= 65535:
                raise ValueError
            tcp = (host, port)
        except ValueError:
            build_parser().error("--tcp must be HOST:PORT with a port from 1 to 65535")
    report = run_diagnostics(dns=args.dns, tcp=tcp, url=args.url, disk_path=args.disk_path)
    rendered = to_json(report) if args.format == "json" else to_text(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 1 if report["summary"]["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
