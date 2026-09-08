"""Coordinate policy, snapshot selection, counting, and reporting."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from . import __version__
from .measure import PINNED_TOKENIZER, encoding_for, measure
from .policy import PolicyError, REVIEW_GUIDANCE, matches, parse, relative_path, select
from .report import emit, finish
from .source import Repository


def checker_triggers(root: Path) -> list[str]:
    utility = Path(__file__).resolve().parents[1]
    try:
        relative = utility.relative_to(root).as_posix()
    except ValueError:
        return []
    if relative == ".":
        return ["check.py", "token_budgets/**"]
    return [relative, relative + "/**"]


def verify_checker(repo: Repository) -> None:
    """Reject a staged gitlink checked by a different or dirty utility version."""
    utility = Path(__file__).resolve().parents[1]
    try:
        relative = utility.relative_to(repo.root).as_posix()
    except ValueError:
        return
    if not repo.staged:
        return
    entry = repo.entries.get(relative)
    if not entry or entry[0] != "160000":
        for path in [utility / "check.py", *sorted((utility / "token_budgets").glob("*.py"))]:
            name = path.relative_to(repo.root).as_posix()
            if path.is_symlink() or repo.read(name) != path.read_bytes():
                raise PolicyError("utility execution files differ from the index; align their working-tree and staged versions before checking")
        return
    head = repo.git("-C", str(utility), "rev-parse", "HEAD").strip().decode("ascii")
    if head != entry[1]:
        raise PolicyError("utility checkout differs from the staged submodule commit; initialize/update the submodule to the staged revision")
    dirty = repo.git("-C", str(utility), "status", "--porcelain", "--untracked-files=all", "--", "check.py", "token_budgets")
    if dirty:
        raise PolicyError("utility execution files have local changes; commit the utility and stage its submodule revision before checking")


def collect(repo: Repository, config_path: str, report: dict, all_files: bool) -> None:
    raw = repo.read(config_path)
    policy = parse(raw)
    report["config_sha256"] = hashlib.sha256(raw).hexdigest()
    report["encoding"] = policy["encoding"]
    triggers = [config_path, ".gitmodules", *checker_triggers(repo.root), *policy.get("full_scan_on", [])]
    triggered = sorted(path for path in repo.changed if any(matches(path, glob) for glob in triggers))
    full = not repo.staged or all_files or bool(triggered)
    report["scope"] = "index-full" if repo.staged and full else "index-staged" if repo.staged else "worktree-full"
    report["full_scan_triggers"] = triggered if repo.staged else []
    report["coverage"]["inventory_files"] = len(repo.paths)
    report["coverage"]["inventory"] = "tracked index" if repo.staged else "tracked paths plus untracked nonignored paths"
    report["coverage"]["gitignored_untracked"] = "outside Git source inventory; add with git add -f to include"
    selected = []
    for path in sorted(repo.paths):
        budget, reason = select(path, policy)
        if budget is None:
            report["excluded"].append({"path": path, "reason": reason})
        elif full or path in repo.changed:
            selected.append((path, budget))
        else:
            report["coverage"]["unchanged_files"] += 1
    if full and not selected:
        raise PolicyError("no files selected for a full check; review include/exclude globs and Git inventory")
    verify_checker(repo)
    encoding = encoding_for(policy["encoding"], report["tokenizer"])
    for path, budget in selected:
        try:
            report["files"].append(measure(path, repo.read(path), budget, encoding))
        except PolicyError as error:
            report["errors"].append(str(error))
    repo.verify_index()


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local read-only token budgets for repository docs and code.")
    parser.add_argument("--root", type=Path, default=root or Path.cwd(), help="Git repository root (default: current directory)")
    parser.add_argument("--config", default="token-budgets.json", help="repository-relative version 2 JSON policy")
    parser.add_argument("--staged", action="store_true", help="count index blobs with the index policy; auto-expand on policy/checker changes")
    parser.add_argument("--all", action="store_true", help="full worktree scan, or full index scan with --staged")
    parser.add_argument("--check", action="store_true", help="exit 1 for configured error-severity findings (input errors always exit 2)")
    parser.add_argument("--json", action="store_true", help="emit a deterministic metadata-only JSON report")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--details", choices=("findings", "all"), default="findings", help="human output detail; findings always include review guidance")
    args = parser.parse_args(argv)
    report = {
        "report_version": 2, "utility_version": __version__, "counting_policy_version": 1,
        "config": args.config, "config_sha256": None,
        "encoding": None, "encoding_purpose": "repository budget policy, not an exact Codex internal token count",
        "tokenizer": {"package": "tiktoken", "version": None, "required_version": PINNED_TOKENIZER},
        "scope": "index-staged" if args.staged else "worktree-full", "full_scan_triggers": [],
        "coverage": {"inventory_files": 0, "unchanged_files": 0},
        "files": [], "excluded": [], "errors": [], "review_guidance": REVIEW_GUIDANCE,
        "enforced": args.check,
    }
    try:
        relative_path(args.config, "config")
        collect(Repository(args.root, args.staged), args.config, report, args.all)
    except PolicyError as error:
        report["errors"].append(str(error))
    except Exception as error:
        # Do not echo exceptions that can contain source bytes, subprocess output or credentials.
        report["errors"].append(f"check failed ({type(error).__name__}); verify policy fields, Git access, and selected UTF-8 files")
    code = finish(report, args.check)
    emit(report, "json" if args.json else args.format, args.details)
    return code
