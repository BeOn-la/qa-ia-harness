from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .common import CODES, ContractError
from .gate import evaluate
from .reporting import load_report, markdown
from .runner import check, run


def main(argv=None):
    parser = argparse.ArgumentParser(prog="qa-harness", description="QA reproducible sobre un checkout explicito")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "run"):
        sub = subs.add_parser(name)
        sub.add_argument("--repo", required=True, type=Path)
        sub.add_argument("--manifest", default="qa.json")
        sub.add_argument("--profile", required=True)
        if name == "run":
            sub.add_argument("--control", action="append")
            sub.add_argument("--output", help="Directorio nuevo dentro de .qa-runs/")
            sub.add_argument("--retry", type=int, default=0, choices=(0, 1, 2))
            sub.add_argument("--allow-isolated-write", action="store_true",
                             help="Confirma una ejecucion SQL con escritura aislada declarada.")
    sub = subs.add_parser("report")
    sub.add_argument("--input", required=True, type=Path)
    sub = subs.add_parser("gate")
    sub.add_argument("--repo", required=True, type=Path)
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--decisions", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = check(args.repo.resolve(), args.manifest, args.profile)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return CODES[result["status"]]
        if args.command == "run":
            result, destination = run(args.repo, args.manifest, args.profile, args.control, args.output, args.retry,
                                      args.allow_isolated_write)
            print(json.dumps({"status": result["status"], "exit_code": result["exit_code"],
                              "exploratory": result["exploratory"], "report": str(destination / "report.json")},
                             ensure_ascii=False, indent=2))
            return result["exit_code"]
        if args.command == "report":
            print(markdown(load_report(args.input)))
            return 0
        result = evaluate(args.repo, args.input, args.decisions)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result["exit_code"]
    except (ContractError, OSError) as exc:
        print(json.dumps({"status": "error", "exit_code": 2, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('{"status":"cancelled","exit_code":3}', file=sys.stderr)
        return 3
