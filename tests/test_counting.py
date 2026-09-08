"""Counting contracts exercised through the public CLI."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from tests.support import CHECK, RepoCase, fixture_environment, token_count


class CountingTest(RepoCase):
    def test_exact_utf8_bytes_unicode_crlf_and_literal_specials(self) -> None:
        contents = {
            "unicode.md": "Café 中文 🐙 e\u0301\n",
            "crlf.py": b"first\r\nsecond\r\n",
            "special.md": "<|endoftext|> <|fim_prefix|> <|im_start|>\n",
            "empty.txt": b"",
        }
        for path, content in contents.items():
            self.write(path, content)
        report = self.run_check("--all")
        files = self.records(report)
        self.assertEqual(set(files), set(contents))
        for path in contents:
            data = (self.root / path).read_bytes()
            with self.subTest(path=path):
                self.assertEqual(files[path]["tokens"], token_count(data))
                self.assertEqual(files[path]["bytes"], len(data))
                self.assertEqual(files[path]["sha256"], hashlib.sha256(data).hexdigest())
        serialized = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("Café", serialized)
        self.assertNotIn("<|endoftext|>", serialized)


    def test_warning_inclusive_maximum_exclusive(self) -> None:
        data = self.write("file.txt", "one two three four five six")
        count = token_count(data)
        for warn, maximum, status, severity, exit_code in [
            (count + 1, count + 2, "ok", "ok", 0),
            (count, count + 1, "warning", "warning", 0),
            (count - 1, count, "warning", "warning", 0),
            (count - 2, count - 1, "over", "error", 1),
        ]:
            with self.subTest(warn=warn, maximum=maximum):
                self.write_policy(self.tight_policy(warning=warn, maximum=maximum))
                record = self.records(self.run_check(expected=exit_code))["file.txt"]
                self.assertEqual(record["status"], status)
                self.assertEqual(record["severity"], severity)
                self.assertEqual(record["warn_tokens"], warn)
                self.assertEqual(record["max_tokens"], maximum)


    def test_severity_messages_and_diagnostics_only_exit_status(self) -> None:
        self.write("file.txt", "one two three four five six")
        self.write_policy(self.tight_policy(
            warning=1, maximum=2, max_severity="warning", max_message="Review the public interface."))
        record = self.records(self.run_check())["file.txt"]
        self.assertEqual((record["status"], record["severity"]), ("over", "warning"))
        self.assertEqual(record["message"], "Review the public interface.")
        self.write_policy(self.tight_policy(
            warning=1, maximum=100, warn_severity="error", warn_message="Review responsibilities."))
        record = self.records(self.run_check(expected=1))["file.txt"]
        self.assertEqual((record["status"], record["severity"]), ("warning", "error"))
        self.assertEqual(record["message"], "Review responsibilities.")
        self.run_check(check=False)


    def test_human_output_and_json_enforce_identical_severity(self) -> None:
        self.write_policy(self.tight_policy(warning=1, maximum=2))
        self.write("file.txt", "one two three four five six")
        report = self.run_check(expected=1)
        result = subprocess.run(
            [sys.executable, str(CHECK), "--root", str(self.root), "--config", "budget.json", "--check"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            env=fixture_environment(),
        )
        self.assertEqual(result.returncode, report["exit_code"])
        text = (result.stdout + result.stderr).decode()
        self.assertIn("file.txt", text)
        self.assertIn("Review cohesive boundaries and dependency direction.", text)
        self.assertNotIn("one two three", text)


    def test_cached_counting_works_with_network_disabled_in_fresh_process(self) -> None:
        self.write("file.txt", "cached offline counting 中文\n")
        online = self.run_check()
        with tempfile.TemporaryDirectory(prefix="token-budgets-no-network-") as directory:
            Path(directory, "sitecustomize.py").write_text(
                "import socket\n"
                "def forbidden(*args, **kwargs):\n"
                "    raise RuntimeError('network forbidden by offline test')\n"
                "socket.create_connection = forbidden\n"
                "socket.socket.connect = forbidden\n"
                "socket.getaddrinfo = forbidden\n",
                encoding="utf-8",
            )
            offline = self.run_check(env={"PYTHONPATH": directory})
        self.assertEqual(offline, online)
