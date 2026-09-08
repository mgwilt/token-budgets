"""Selection contracts exercised through the public CLI."""

import os

from tests.support import RepoCase, policy


class SelectionTest(RepoCase):
    def test_full_check_includes_tracked_and_nonignored_untracked(self) -> None:
        self.write("tracked.txt", "tracked")
        self.commit("tracked.txt")
        self.write("untracked.py", "print('hello')\n")
        self.write(".gitignore", "ignored/\n")
        self.write("ignored/output.txt", "ignored")
        expected = {"tracked.txt", "untracked.py"}
        self.assertEqual(set(self.records(self.run_check())), expected)
        self.assertEqual(set(self.records(self.run_check("--all"))), expected)


    def test_empty_staged_change_is_success_and_empty_full_selection_is_error(self) -> None:
        self.assertEqual(self.run_check("--staged")["files"], [])
        self.run_check("--all", expected=2)


    def test_initial_index_delete_and_rename(self) -> None:
        self.git("update-ref", "-d", "HEAD")
        self.write("initial.txt", "initial")
        self.stage("initial.txt")
        self.assertEqual(set(self.records(self.run_check("--staged"))), {"initial.txt"})
        self.git("commit", "--quiet", "-m", "test: first commit")
        self.git("mv", "--", "initial.txt", "renamed file.txt")
        self.assertEqual(set(self.records(self.run_check("--staged"))), {"renamed file.txt"})
        self.git("commit", "--quiet", "-m", "test: rename")
        self.git("rm", "--", "renamed file.txt")
        self.assertEqual(self.run_check("--staged")["files"], [])


    def test_filenames_with_spaces_newlines_unicode_and_leading_dash(self) -> None:
        paths = [
            "space name.py", "new\nline.md", "-leading.txt", "unicodé/中文.rs",
            "'single' and \"double\".py", "`printf ignored`;$(printf ignored)&|.txt",
        ]
        if os.name != "nt":
            paths.append(r"literal\backslash.py")
        for path in paths:
            self.write(path, "hello")
        self.stage(*paths)
        self.assertEqual(set(self.records(self.run_check("--staged"))), set(paths))
        self.assertEqual(set(self.records(self.run_check("--all"))), set(paths))


    def test_selected_gitlink_requires_explicit_exclusion(self) -> None:
        head = self.git("rev-parse", "HEAD").decode().strip()
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},vendor/module")
        self.run_check("--staged", expected=2)
        value = policy()
        value["exclude"].append({"glob": "vendor/**", "reason": "Dependency submodule has its own policy."})
        self.write_policy(value)
        self.write("valid.txt", "hello")
        self.stage("budget.json", "valid.txt")
        self.assertEqual(set(self.records(self.run_check("--staged"))), {"valid.txt"})


    def test_unmerged_index_is_actionable_error(self) -> None:
        blob_a = self.git("hash-object", "-w", "--stdin", input=b"ancestor\n").decode().strip()
        blob_b = self.git("hash-object", "-w", "--stdin", input=b"ours\n").decode().strip()
        blob_c = self.git("hash-object", "-w", "--stdin", input=b"theirs\n").decode().strip()
        entries = "".join(f"100644 {blob} {stage}\tconflict.txt\n"
                          for stage, blob in enumerate([blob_a, blob_b, blob_c], 1))
        self.git("update-index", "--index-info", input=entries.encode())
        self.run_check("--staged", expected=2)


    def test_deleted_staged_policy_is_error(self) -> None:
        self.git("rm", "--", "budget.json")
        self.write("file.txt", "hello")
        self.stage("file.txt")
        self.run_check("--staged", expected=2)


    def test_missing_tracked_selected_file_is_error_in_worktree_only(self) -> None:
        self.write("missing.txt", "hello")
        self.commit("missing.txt")
        (self.root / "missing.txt").unlink()
        self.run_check(expected=2)
        self.assertEqual(set(self.records(self.run_check("--all", "--staged"))), {"missing.txt"})
