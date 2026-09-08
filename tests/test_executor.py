"""Staged snapshots must be checked by their corresponding executor version."""

from pathlib import Path
import shutil
import tempfile

from tests.support import CHECK, RepoCase


class ExecutorTest(RepoCase):
    def copy_executor(self, destination: Path) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CHECK, destination / "check.py")
        shutil.copytree(CHECK.parent / "token_budgets", destination / "token_budgets",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (destination / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        return destination / "check.py"

    def test_root_executor_must_equal_staged_execution_files(self) -> None:
        checker = self.copy_executor(self.root)
        self.write_policy(self.tight_policy(warning=9000, maximum=10000))
        self.stage("budget.json", "check.py", "token_budgets", ".gitignore")
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
        self.run_check("--all", "--staged", checker=checker)
        checker.write_bytes(checker.read_bytes() + b"\n# local utility change\n")
        report = self.run_check("--all", "--staged", checker=checker, expected=2)
        self.assertTrue(any("local changes" in error for error in report["errors"]))
        self.git("-C", str(utility), "add", "--", "check.py")
        self.git("-C", str(utility), "commit", "--quiet", "-m", "test: next executor")
        report = self.run_check("--all", "--staged", checker=checker, expected=2)
        self.assertTrue(any("submodule commit" in error for error in report["errors"]))
        self.stage("tools/token-budgets")
        report = self.run_check("--staged", checker=checker)
        self.assertEqual(report["scope"], "index-full")
        self.assertIn("file.txt", self.records(report))
