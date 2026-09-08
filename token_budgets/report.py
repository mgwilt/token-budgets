"""One report contract for human diagnostics and machine consumers."""

import json
import sys

from .policy import REVIEW_GUIDANCE, display


def finish(report: dict, check: bool) -> int:
    records = report["files"]
    report["summary"] = {
        "files": len(records),
        "tokens": sum(item["tokens"] for item in records),
        "over_budget": sum(item["status"] == "over" for item in records),
        "warnings": sum(item["severity"] == "warning" for item in records),
        "violations": sum(item["severity"] == "error" for item in records),
        "errors": len(report["errors"]),
        "excluded": len(report["excluded"]),
    }
    code = 2 if report["errors"] else 1 if check and report["summary"]["violations"] else 0
    report["exit_code"] = code
    return code


def emit(report: dict, output: str, details: str) -> None:
    if output == "json":
        print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
        return
    summary = report["summary"]
    print(f"{summary['files']} files, {summary['tokens']} tokens, {summary['warnings']} warnings, "
          f"{summary['violations']} violations, {summary['errors']} input errors; "
          f"{report['scope']} / exit {report['exit_code']}")
    print(f"Coverage: {report['coverage']['inventory_files']} inventoried, {summary['excluded']} explicitly omitted; "
          f"{report['coverage']['unchanged_files']} unchanged files deferred.")
    for item in report["files"]:
        if details == "all" or item["severity"] != "ok":
            print(f"{item['severity']}: {display(item['path'])}: {item['tokens']} tokens "
                  f"(warn >= {item['warn_tokens']}, max {item['max_tokens']})")
            if item["message"]:
                print("  " + item["message"])
            if details == "all":
                print(f"  sha256={item['sha256']} bytes={item['bytes']}")
    if details == "all":
        for item in report["excluded"]:
            print(f"excluded: {display(item['path'])}: {item['reason']}")
    if summary["warnings"] or summary["violations"]:
        print("Architecture review: " + REVIEW_GUIDANCE)
    for error in report["errors"]:
        print("token-budgets: " + error, file=sys.stderr)
