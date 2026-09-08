"""Staged contracts exercised through the public CLI."""

import hashlib

from tests.support import RepoCase, policy, token_count


class StagedTest(RepoCase):
    def test_staged_content_and_policy_ignore_unstaged_versions(self) -> None:
        value = self.tight_policy(warning=3, maximum=5)
        self.write_policy(value)
        self.commit("budget.json")
        staged_data = self.write("partial.txt", "one two")
        self.stage("partial.txt")
        self.write("partial.txt", "one two three four five six seven eight nine ten")
        self.write_policy(self.tight_policy(warning=0, maximum=1))
        record = self.records(self.run_check("--staged"))["partial.txt"]
        self.assertEqual(record["tokens"], token_count(staged_data))
        self.assertEqual(record["sha256"], hashlib.sha256(staged_data).hexdigest())
        self.assertEqual(record["max_tokens"], 5)
        self.run_check(expected=1)


    def test_staged_overage_is_not_hidden_by_short_worktree_file(self) -> None:
        self.write_policy(self.tight_policy(warning=2, maximum=3))
        self.commit("budget.json")
        staged_data = self.write("partial.txt", "one two three four five six")
        self.stage("partial.txt")
        self.write("partial.txt", "one")
        record = self.records(self.run_check("--staged", expected=1))["partial.txt"]
        self.assertEqual(record["tokens"], token_count(staged_data))
        self.run_check()


    def test_staged_policy_changes_force_full_index_and_use_staged_policy(self) -> None:
        self.write("unchanged.txt", "one two three four five six")
        self.commit("unchanged.txt")
        self.write_policy(self.tight_policy(warning=1, maximum=2))
        self.stage("budget.json")
        self.write_policy(policy())
        report = self.run_check("--staged", expected=1)
        record = self.records(report)["unchanged.txt"]
        self.assertEqual(record["max_tokens"], 2)


    def test_configured_checker_changes_force_full_index(self) -> None:
        self.write("unchanged.txt", "one two three four five six")
        self.write_policy(self.tight_policy(warning=1, maximum=2))
        self.commit("unchanged.txt", "budget.json")
        self.write("scripts/check.sh", "true\n")
        self.stage("scripts/check.sh")
        files = self.records(self.run_check("--staged", expected=1))
        self.assertEqual(set(files), {"scripts/check.sh", "unchanged.txt"})


    def test_staged_selection_and_explicit_all_index(self) -> None:
        self.write("unchanged.txt", "unchanged")
        self.commit("unchanged.txt")
        self.write("changed.txt", "changed")
        self.stage("changed.txt")
        self.write("untracked.txt", "untracked")
        self.assertEqual(set(self.records(self.run_check("--staged"))), {"changed.txt"})
        self.assertEqual(set(self.records(self.run_check("--staged", "--all"))),
                         {"changed.txt", "unchanged.txt"})
