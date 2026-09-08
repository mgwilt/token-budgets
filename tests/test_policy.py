"""Policy contracts exercised through the public CLI."""

import json

from tests.support import RepoCase, policy


class PolicyTest(RepoCase):
    def test_invalid_explicit_rule_relationships_fail_even_without_matching_files(self) -> None:
        self.write("file.txt", "hello")
        for overrides in [
            {"max_tokens": 1, "warn_tokens": 2},
            {"warn_severity": "error", "max_severity": "warning"},
        ]:
            with self.subTest(overrides=overrides):
                value = policy(rules=[{
                    "glob": "absent/**", "reason": "No file needs to match for validation.",
                    **overrides,
                }])
                self.write_policy(value)
                report = self.run_check(expected=2)
                self.assertTrue(any("rule" in error for error in report["errors"]))
                self.stage("budget.json", "file.txt")
                self.run_check("--staged", expected=2)


    def test_globs_exclusions_and_cumulative_last_rule_precedence(self) -> None:
        value = self.tight_policy(warning=20, maximum=30)
        value["include"] = ["*.py", "docs/**/*.md", "src/**"]
        value["exclude"].append({"glob": "docs/archive/**", "reason": "Immutable source archive."})
        value["rules"] = [
            {"glob": "docs/**", "reason": "Readable docs.", "warn_tokens": 5, "max_tokens": 10},
            {"glob": "docs/**/*.md", "reason": "Markdown guidance.", "warn_message": "Review document scope."},
            {"glob": "docs/index.md", "reason": "Short navigation.", "max_tokens": 7},
            {"glob": "docs/archive/**", "reason": "Cannot override exclusions.", "max_tokens": 1},
        ]
        self.write_policy(value)
        for path in ["root.py", "nested/no.py", "docs/index.md", "docs/deep/guide.md",
                     "docs/archive/research.md", "src/lib/code.rs", "unselected.txt"]:
            self.write(path, "hello")
        files = self.records(self.run_check())
        self.assertEqual(set(files), {"root.py", "docs/index.md", "docs/deep/guide.md", "src/lib/code.rs"})
        self.assertEqual(files["root.py"]["max_tokens"], 30)
        self.assertEqual(files["docs/index.md"]["warn_tokens"], 5)
        self.assertEqual(files["docs/index.md"]["max_tokens"], 7)
        self.assertEqual(files["docs/deep/guide.md"]["max_tokens"], 10)


    def test_malformed_unknown_and_duplicate_policy_keys_are_errors(self) -> None:
        self.write("file.txt", "hello")
        bad_policies: list[str] = ["{", '{"version":2,"version":2}']
        value = policy()
        value["misspelled_option"] = True
        bad_policies.append(json.dumps(value))
        value = policy()
        value["defaults"]["max_toknes"] = 3
        bad_policies.append(json.dumps(value))
        bad_policies.append(json.dumps(policy()).replace('"max_tokens": 2000', '"max_tokens": 2000, "max_tokens": 2001'))
        for raw in bad_policies:
            with self.subTest(raw=raw):
                self.write("budget.json", raw)
                self.run_check(expected=2)


    def test_invalid_policy_types_thresholds_and_required_exclusion_reasons(self) -> None:
        self.write("file.txt", "hello")
        cases = []
        for field, invalid in [("max_tokens", True), ("max_tokens", -1),
                               ("warn_tokens", 2001), ("warn_tokens", 1.5),
                               ("max_severity", "fatal"), ("warn_message", 7)]:
            value = policy()
            value["defaults"][field] = invalid
            cases.append(value)
        cases.extend([
            policy(version=1), policy(include="**"),
            policy(exclude=[{"glob": "vendor/**"}]),
            policy(exclude=[{"glob": "vendor/**", "reason": ""}]),
            policy(rules=[{"glob": "**", "reason": "test", "unknown": 1}]),
        ])
        for value in cases:
            with self.subTest(value=value):
                self.write_policy(value)
                self.run_check(expected=2)
                self.run_check(expected=2, check=False)
