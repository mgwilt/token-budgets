"""Shared real-repository fixture and strict CLI report assertions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import tiktoken


CHECK = Path(__file__).resolve().parents[1] / "check.py"
ENCODING = tiktoken.get_encoding("o200k_base")


def token_count(content: bytes) -> int:
    return len(ENCODING.encode(content.decode("utf-8"), disallowed_special=()))


def policy(**overrides: object) -> dict:
    result = {
        "version": 2,
        "encoding": "o200k_base",
        "include": ["**"],
        "exclude": [
            {"glob": "budget.json", "reason": "Policy metadata is validated separately."},
            {"glob": ".gitignore", "reason": "Test repository ignore metadata."},
        ],
        "defaults": {
            "max_tokens": 2000,
            "warn_tokens": 1500,
            "warn_severity": "warning",
            "max_severity": "error",
            "warn_message": "Review responsibilities, interfaces, and tests.",
            "max_message": "Review cohesive boundaries and dependency direction.",
        },
        "rules": [],
        "full_scan_on": ["scripts/**", "lefthook.yml"],
    }
    result.update(overrides)
    return result


class RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="token-budgets-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Token Budget Tests")
        self.git("config", "user.email", "tests@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.write_policy(policy())
        self.commit("budget.json")


    def git(self, *arguments: str, input: bytes | None = None,
            env: dict[str, str] | None = None) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            input=input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env={**os.environ, **(env or {})},
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result.stdout


    def write(self, path: str, content: str | bytes) -> bytes:
        data = content.encode("utf-8") if isinstance(content, str) else content
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return data


    def write_policy(self, value: dict) -> None:
        self.write("budget.json", json.dumps(value, ensure_ascii=False, indent=2) + "\n")


    def stage(self, *paths: str) -> None:
        self.git("add", "--", *paths)


    def commit(self, *paths: str) -> None:
        self.stage(*paths)
        self.git("commit", "--quiet", "-m", "test: establish baseline")


    def run_check(
        self, *arguments: str, expected: int = 0, check: bool = True,
        env: dict[str, str] | None = None, checker: Path | None = None,
    ) -> dict:
        command = [sys.executable, str(checker or CHECK), "--root", str(self.root),
                   "--config", "budget.json", "--json"]
        if check:
            command.append("--check")
        command.extend(arguments)
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            env={**os.environ, **(env or {})},
        )
        self.assertEqual(result.returncode, expected, result.stdout.decode(errors="replace")
                         + result.stderr.decode(errors="replace"))
        try:
            report = json.loads(result.stdout)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.fail(f"Expected one JSON report, received {result.stdout!r}; stderr={result.stderr!r}")
        self.assertEqual(report["exit_code"], result.returncode)
        self.assertIsInstance(report["files"], list)
        self.assertIsInstance(report["errors"], list)
        if expected == 2:
            self.assertTrue(report["errors"], report)
        else:
            self.assertEqual(report["errors"], [], report)
        return report


    def records(self, report: dict) -> dict[str, dict]:
        return {record["path"]: record for record in report["files"]}


    def tight_policy(self, *, warning: int, maximum: int, **extra: object) -> dict:
        value = policy()
        value["defaults"].update(warn_tokens=warning, max_tokens=maximum, **extra)
        return value
