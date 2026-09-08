"""Safety contracts exercised through the public CLI."""

import json

from tests.support import RepoCase, policy


class SafetyTest(RepoCase):
    def test_selected_binary_and_non_utf8_files_require_explicit_exclusion(self) -> None:
        for content in [b"private-source\x00payload", b"private-source\xffpayload"]:
            with self.subTest(content=content):
                self.write("asset.bin", content)
                report = self.run_check(expected=2)
                self.assertNotIn("private-source", json.dumps(report))
                self.stage("asset.bin")
                self.run_check("--staged", expected=2)
        value = policy()
        value["exclude"].append({"glob": "*.bin", "reason": "Opaque binary fixture assets."})
        self.write_policy(value)
        self.write("valid.py", "pass\n")
        self.run_check()
        self.stage("budget.json", "valid.py")
        self.run_check("--staged")


    def test_selected_symlink_is_error_even_when_its_target_is_readable(self) -> None:
        self.write("target.txt", "private source content")
        (self.root / "link.txt").symlink_to("target.txt")
        self.run_check(expected=2)
        self.stage("link.txt", "target.txt")
        self.run_check("--staged", expected=2)
        value = policy()
        value["exclude"].append({"glob": "link.txt", "reason": "Symlink is not repository source."})
        self.write_policy(value)
        self.stage("budget.json")
        self.assertEqual(set(self.records(self.run_check("--staged"))), {"target.txt"})


    def test_run_is_read_only_and_json_is_deterministic(self) -> None:
        self.write("partial.txt", "one two three")
        self.stage("partial.txt")
        self.write("partial.txt", "changed worktree\r\n")
        before_index = (self.root / ".git" / "index").read_bytes()
        before_status = self.git("status", "--porcelain=v1", "-z")
        before_files = {str(p.relative_to(self.root)): p.read_bytes()
                        for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}
        first = self.run_check("--staged")
        second = self.run_check("--staged")
        self.assertEqual(first, second)
        self.assertEqual((self.root / ".git" / "index").read_bytes(), before_index)
        self.assertEqual(self.git("status", "--porcelain=v1", "-z"), before_status)
        after_files = {str(p.relative_to(self.root)): p.read_bytes()
                       for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(after_files, before_files)
