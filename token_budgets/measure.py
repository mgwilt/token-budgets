"""Exact UTF-8 counting, dependency provenance and threshold evaluation."""

import hashlib
import importlib.metadata

from .policy import PolicyError, display

PINNED_TOKENIZER = "0.14.0"


def encoding_for(name: str, tokenizer: dict):
    try:
        import tiktoken
        installed = importlib.metadata.version("tiktoken")
        tokenizer["version"] = installed
        if installed != PINNED_TOKENIZER:
            raise PolicyError(f"expected tiktoken {PINNED_TOKENIZER}; run the pinned check.py script with uv")
        return tiktoken.get_encoding(name)
    except PolicyError:
        raise
    except Exception as error:
        raise PolicyError(
            "tokenizer setup failed; run `uv run --script <utility>/check.py --check` with dependency/network "
            "access once to cache the pinned package and public encoding data. Set TIKTOKEN_CACHE_DIR "
            "to a persistent writable cache if needed. Source text is never uploaded. "
            f"Failure type: {type(error).__name__}"
        ) from error


def measure(path: str, raw: bytes, budget: dict, encoding) -> dict:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise PolicyError(f"selected file {display(path)} is not UTF-8; explicitly exclude binary/generated content with a reason") from error
    if "\0" in text:
        raise PolicyError(f"selected file {display(path)} contains NUL bytes; explicitly exclude binary content with a reason")
    count = len(encoding.encode(text, disallowed_special=()))
    status = "over" if count > budget["max_tokens"] else "warning" if count >= budget["warn_tokens"] else "ok"
    prefix = "max" if status == "over" else "warn"
    return {
        "path": path, "tokens": count, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "max_tokens": budget["max_tokens"], "warn_tokens": budget["warn_tokens"],
        "status": status, "severity": budget[prefix + "_severity"] if status != "ok" else "ok",
        "message": budget[prefix + "_message"] if status != "ok" else "",
        "rules": budget["rules"],
    }
