"""Standalone stdin and Python counting contract, without a Git repository."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import tiktoken

COUNT = Path(__file__).resolve().parents[1] / "count.py"
ENCODING = tiktoken.get_encoding("o200k_base")


class CountAPI(unittest.TestCase):
    def run_count(self, raw, *args, expected=0, code=None):
        with tempfile.TemporaryDirectory(prefix="token-count-nonrepo-") as directory:
            result = subprocess.run(
                [sys.executable, "-c", code] if code else [sys.executable, str(COUNT), *args],
                input=raw, capture_output=True, cwd=directory,
                env={**os.environ, "PATH": "", "GIT_DIR": "/not-a-git-repository"},
            )
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(result.returncode, expected, result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace"))
        self.assertEqual(result.stderr, b"")
        report = json.loads(result.stdout)
        self.assertEqual(report["exit_code"], result.returncode)
        return report

    def assert_provenance(self, report, raw):
        self.assertEqual(report["report_version"], 1)
        self.assertEqual(report["counting_policy_version"], 1)
        self.assertEqual(report["encoding"], "o200k_base")
        self.assertEqual(report["tokenizer"]["package"], "tiktoken")
        self.assertEqual(report["tokenizer"]["required_version"], "0.14.0")
        self.assertTrue(report["utility_version"])
        self.assertEqual(report["bytes"], len(raw))
        self.assertEqual(report["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIn("not an exact", report["encoding_purpose"])

    def test_exact_stdin_bytes_empty_unicode_crlf_nul_and_specials(self):
        payloads = [b"", "---\r\ncafé 世界 🦀\r\n<|endoftext|>\r\n[^s]: citation\r\n".encode(), b"a\x00b"]
        for raw in payloads:
            with self.subTest(raw=raw):
                report = self.run_count(raw, "--encoding", "o200k_base")
                self.assert_provenance(report, raw)
                self.assertEqual(report["tokens"], len(ENCODING.encode(raw.decode(), disallowed_special=())))
                self.assertEqual(report["tokenizer"]["version"], "0.14.0")
                self.assertEqual(report["errors"], [])

    def test_deterministic_metadata_and_python_api_agree_without_source(self):
        from token_budgets.count import count_bytes
        raw = b"PRIVATE_CONTENT_SENTINEL: entire rendered preview including expansion metadata\r\n" * 1024
        first = self.run_count(raw)
        self.assertGreater(first["tokens"], 4000)
        self.assert_provenance(first, raw)
        self.assertEqual(first, self.run_count(raw, "--json"))
        self.assertEqual(first, count_bytes(raw))
        self.assertNotIn("PRIVATE_CONTENT_SENTINEL", json.dumps(first))
        self.assertNotIn("files", first)

    def test_invalid_utf8_and_unknown_encoding_have_safe_json_errors(self):
        raw = b"PRIVATE_CONTENT_SENTINEL\xff"
        report = self.run_count(raw, expected=2)
        self.assert_provenance(report, raw)
        self.assertIsNone(report["tokens"])
        self.assertIn("UTF-8", " ".join(report["errors"]))
        self.assertNotIn("PRIVATE_CONTENT_SENTINEL", json.dumps(report))
        report = self.run_count(b"valid text", "--encoding", "not-an-encoding", expected=2)
        self.assertIsNone(report["tokens"])
        self.assertTrue(report["errors"])

    def test_cached_offline_fresh_interpreter(self):
        raw = "offline 世界\r\n<|endoftext|>".encode()
        code = (
            "import sys,runpy,socket,requests;"
            "deny=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('network disabled'));"
            "requests.sessions.Session.request=deny;socket.socket.connect=deny;socket.getaddrinfo=deny;"
            f"sys.path.insert(0,{str(COUNT.parent)!r});sys.argv=[{str(COUNT)!r}];"
            f"runpy.run_path({str(COUNT)!r},run_name='__main__')"
        )
        report = self.run_count(raw, code=code)
        self.assertEqual(report["tokens"], len(ENCODING.encode(raw.decode(), disallowed_special=())))

    def test_stdin_read_failure_returns_json_without_exception_contents(self):
        from token_budgets.count import main
        source = SimpleNamespace(buffer=SimpleNamespace(read=lambda: (_ for _ in ()).throw(OSError("PRIVATE_READ_SENTINEL"))))
        output, errors = io.StringIO(), io.StringIO()
        with patch("sys.stdin", source), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main([])
        report = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(report["exit_code"], status)
        self.assertIsNone(report["tokens"])
        self.assertIsNone(report["bytes"])
        self.assertIsNone(report["sha256"])
        self.assertTrue(report["errors"])
        self.assertEqual(errors.getvalue(), "")
        self.assertNotIn("PRIVATE_READ_SENTINEL", output.getvalue())
