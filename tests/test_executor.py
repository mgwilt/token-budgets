"""Staged snapshots must be checked by their corresponding executor version."""

import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from tests.support import CHECK, RepoCase, fixture_environment


class ExecutorTest(RepoCase):
    def test_inherited_hook_environment_preserves_calling_repository(self) -> None:
        self.git("config", "user.name", "Caller identity must remain unchanged")
        caller_git = self.root / ".git"
        before = {name: (caller_git / name).read_bytes() for name in ("config", "index", "HEAD")}
        commit = self.git("rev-parse", "HEAD")
        inherited = {
            "GIT_DIR": str(caller_git), "GIT_WORK_TREE": str(self.root),
            "GIT_INDEX_FILE": str(caller_git / "index"), "GIT_PREFIX": "caller/",
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.email",
            "GIT_CONFIG_VALUE_0": "inherited@example.invalid",
            "LEFTHOOK": "1", "LEFTHOOK_BIN": "/unavailable-inherited-hook",
        }
        nested = RepoCase()
        try:
            with patch.dict(os.environ, inherited):
                isolated = fixture_environment()
                self.assertFalse(any(name.startswith(("GIT_", "LEFTHOOK")) for name in isolated))
                self.assertEqual(fixture_environment({"GIT_INDEX_FILE": "explicit-index"})["GIT_INDEX_FILE"], "explicit-index")
                nested.setUp()
                nested.write("nested.txt", "only the disposable fixture may stage this content")
                nested.commit("nested.txt")
                report = nested.run_check("--staged", "--all")
                self.assertEqual(set(nested.records(report)), {"nested.txt"})
        finally:
            nested.doCleanups()
        self.assertEqual({name: (caller_git / name).read_bytes() for name in before}, before)
        self.assertEqual(self.git("rev-parse", "HEAD"), commit)
        self.assertFalse((self.root / "nested.txt").exists())

    def copy_executor(self, destination: Path) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("check.py", "count.py"):
            shutil.copy2(CHECK.parent / name, destination / name)
        shutil.copytree(CHECK.parent / "token_budgets", destination / "token_budgets",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (destination / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        return destination / "check.py"

    def test_root_executor_must_equal_staged_execution_files(self) -> None:
        checker = self.copy_executor(self.root)
        self.write_policy(self.tight_policy(warning=9000, maximum=10000))
        self.stage("budget.json", "check.py", "count.py", "token_budgets", ".gitignore")
        self.run_check("--staged", checker=checker)
        original = checker.read_bytes()
        checker.write_bytes(original + b"\n# harmless unstaged executor change\n")
        report = self.run_check("--staged", checker=checker, expected=2)
        self.assertTrue(any("index" in error for error in report["errors"]))
        self.stage("check.py")
        self.run_check("--staged", checker=checker)
        package_file = self.root / "token_budgets" / "report.py"
        package_file.write_bytes(package_file.read_bytes() + b"\n# unstaged package change\n")
        self.run_check("--staged", checker=checker, expected=2)

    def test_submodule_executor_must_be_clean_and_match_staged_gitlink(self) -> None:
        remote_temp = tempfile.TemporaryDirectory(prefix="token-budgets-origin-")
        self.addCleanup(remote_temp.cleanup)
        origin = Path(remote_temp.name)
        self.copy_executor(origin)
        self.git("-C", str(origin), "init", "--quiet")
        self.git("-C", str(origin), "config", "user.name", "Token Budget Tests")
        self.git("-C", str(origin), "config", "user.email", "tests@example.invalid")
        self.git("-C", str(origin), "add", "--", ".")
        self.git("-C", str(origin), "commit", "--quiet", "-m", "test: initial executor")
        self.git("-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
                 str(origin), "tools/token-budgets")
        utility = self.root / "tools" / "token-budgets"
        checker = utility / "check.py"
        self.git("-C", str(utility), "config", "user.name", "Token Budget Tests")
        self.git("-C", str(utility), "config", "user.email", "tests@example.invalid")
        value = self.tight_policy(warning=9000, maximum=10000)
        value["exclude"].append({"glob": "tools/**", "reason": "Dependency executor is verified separately."})
        self.write_policy(value)
        self.write("file.txt", "hello")
        self.commit("budget.json", "file.txt", ".gitmodules", "tools/token-budgets")
        hook_env = {
            "GIT_DIR": str(self.root / ".git"),
            "GIT_WORK_TREE": str(self.root),
            "GIT_INDEX_FILE": str(self.root / ".git" / "index"),
            "GIT_PREFIX": "caller/",
        }
        self.run_check("--all", "--staged", checker=checker, env=hook_env)
        parent_index = (self.root / ".git" / "index").read_bytes()
        alternate_index = self.root / ".git" / "alternate-index"
        alternate_index.write_bytes(parent_index)
        alternate_env = {**hook_env, "GIT_INDEX_FILE": str(alternate_index)}
        self.write("alternate.txt", "staged only in the alternate parent index")
        self.git("add", "--", "alternate.txt", env=alternate_env)
        alternate_report = self.run_check("--staged", checker=checker, env=alternate_env)
        self.assertEqual(set(self.records(alternate_report)), {"alternate.txt"})
        self.assertEqual(self.run_check("--staged", checker=checker, env=hook_env)["files"], [])
        self.assertEqual((self.root / ".git" / "index").read_bytes(), parent_index)
        checker.write_bytes(checker.read_bytes() + b"\n# local utility change\n")
        report = self.run_check("--all", "--staged", checker=checker, expected=2, env=hook_env)
        self.assertTrue(any("local changes" in error for error in report["errors"]))
        self.git("-C", str(utility), "add", "--", "check.py")
        self.git("-C", str(utility), "commit", "--quiet", "-m", "test: next executor")
        report = self.run_check("--all", "--staged", checker=checker, expected=2, env=hook_env)
        self.assertTrue(any("submodule commit" in error for error in report["errors"]))
        self.stage("tools/token-budgets")
        report = self.run_check("--staged", checker=checker, env=hook_env)
        self.assertEqual(report["scope"], "index-full")
        self.assertIn("file.txt", self.records(report))
