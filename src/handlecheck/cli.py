"""Command-line interface."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict

from .checkers import PLATFORMS, check_all


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="handlecheck",
        description="Check whether usernames exist on YouTube, TikTok, Instagram, Facebook, X, GitHub and Reddit.",
    )
    p.add_argument("usernames", nargs="*", help="usernames to check (leading @ is optional)")
    p.add_argument("-f", "--file", help="file with one username per line ('-' for stdin)")
    p.add_argument(
        "-p", "--platform", action="append", choices=sorted(PLATFORMS),
        help="limit to a platform (repeatable); default: all",
    )
    p.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p.add_argument("--delay", type=float, default=1.0,
                   help="seconds to wait between usernames (default 1.0, be polite)")
    return p


def read_names(args: argparse.Namespace) -> list[str]:
    names = list(args.usernames)
    if args.file:
        if args.file == "-":
            lines = sys.stdin.read().splitlines()
        else:
            with open(args.file, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        names += [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    return names


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    names = read_names(args)
    if not names:
        build_parser().print_help()
        return 2

    results = []
    for i, name in enumerate(names):
        if i and args.delay:
            time.sleep(args.delay)
        results += check_all(name, args.platform)

    if args.format == "json":
        print(json.dumps([{**asdict(r), "status": r.status.value} for r in results], indent=2))
    elif args.format == "csv":
        w = csv.writer(sys.stdout)
        w.writerow(["username", "platform", "status", "url", "detail"])
        for r in results:
            w.writerow([r.username, r.platform, r.status.value, r.url, r.detail])
    else:
        current = None
        for r in results:
            if r.username != current:
                current = r.username
                print(f"\n== {r.username} ==")
            print(f"  {r.platform:<10} {r.status.value:<10} {r.url}")
    return 0
