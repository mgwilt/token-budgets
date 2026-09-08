"""Complete raw-stdin counting and a deterministic, metadata-only Python API."""

import argparse
import hashlib
import json
import sys

from . import __version__
from .measure import ENCODING_PURPOSE, PINNED_TOKENIZER, count_utf8, encoding_for
from .policy import PolicyError


def _report(encoding_name: str | None) -> dict:
    return {
        "report_version": 1, "utility_version": __version__, "counting_policy_version": 1,
        "encoding": encoding_name, "encoding_purpose": ENCODING_PURPOSE,
        "tokenizer": {"package": "tiktoken", "version": None, "required_version": PINNED_TOKENIZER},
        "tokens": None, "bytes": None, "sha256": None, "errors": [], "exit_code": 0,
    }


def _error(report: dict, message: str) -> dict:
    report["errors"].append(message)
    report["exit_code"] = 2
    return report


def count_bytes(raw: bytes, encoding_name: str = "o200k_base") -> dict:
    """Count exact bytes without Git, source-file access, or normalization."""
    report = _report(encoding_name if isinstance(encoding_name, str) else None)
    if not isinstance(raw, bytes):
        return _error(report, "input must be bytes containing UTF-8 text")
    report["bytes"] = len(raw)
    report["sha256"] = hashlib.sha256(raw).hexdigest()
    if not isinstance(encoding_name, str) or not encoding_name:
        return _error(report, "encoding_name must be a nonempty encoding name")
    try:
        encoding = encoding_for(encoding_name, report["tokenizer"])
        report["tokens"] = count_utf8(raw, encoding)
    except UnicodeError:
        _error(report, "input is not valid UTF-8; provide the original complete UTF-8 bytes")
    except PolicyError as error:
        _error(report, str(error))
    except Exception as error:
        # Exception messages can contain the input; report only their type.
        _error(report, f"counting failed ({type(error).__name__}); verify tokenizer setup and UTF-8 input")
    return report


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid arguments; use --encoding NAME and optional --json; see docs/count.md")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(add_help=False, allow_abbrev=False)
    parser.add_argument("--encoding", default="o200k_base")
    parser.add_argument("--json", action="store_true")
    report = _report("o200k_base")
    try:
        args = parser.parse_args(argv)
    except ValueError as error:
        _error(report, str(error))
    else:
        report = _report(args.encoding)
        try:
            raw = sys.stdin.buffer.read()
        except Exception as error:
            _error(report, f"stdin read failed ({type(error).__name__}); provide a readable byte stream")
        else:
            report = count_bytes(raw, args.encoding)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return report["exit_code"]
