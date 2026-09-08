"""Strict policy validation and explicit, ordered path selection."""

from __future__ import annotations

from fnmatch import fnmatchcase
from functools import lru_cache
import json
import os


class PolicyError(ValueError):
    """An actionable policy or repository input failure."""


REVIEW_GUIDANCE = (
    "Review responsibilities and cohesive boundaries, dependency direction, "
    "interfaces, and tests. For docs, retain evidence and link independently useful leaves. "
    "Token size is a review signal, not proof of architecture quality. "
    "Do not compress, minify, remove checks/types/evidence, or split mechanically to meet a number. "
    "Keep a cohesive file when justified and document a reviewed rule exception."
)
DEFAULT_MESSAGES = {
    "warn_message": "Approaching the token budget: review whether this file has a cohesive responsibility.",
    "max_message": "Above the token budget: review architecture and record a justified resolution.",
}
BUDGET_FIELDS = {
    "max_tokens", "warn_tokens", "warn_severity", "max_severity", *DEFAULT_MESSAGES,
}


def display(path: str) -> str:
    """Keep unusual names readable and prevent terminal-control injection."""
    return json.dumps(path, ensure_ascii=True)


def relative_path(value: object, label: str = "path") -> str:
    if (not isinstance(value, str) or not value or value.startswith("/")
            or (os.name == "nt" and "\\" in value) or "\0" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise PolicyError(f"{label} must be a nonempty repository-relative path without dot segments")
    return value


def pattern(value: object) -> str:
    value = relative_path(value, "glob")
    if any("**" in part and part != "**" for part in value.split("/")):
        raise PolicyError("glob ** must occupy an entire path segment")
    return value


@lru_cache(maxsize=8192)
def matches(path: str, glob: str) -> bool:
    parts, patterns = path.split("/"), glob.split("/")

    @lru_cache(maxsize=None)
    def visit(i: int, j: int) -> bool:
        if j == len(patterns):
            return i == len(parts)
        if patterns[j] == "**":
            return visit(i, j + 1) or (i < len(parts) and visit(i + 1, j))
        return i < len(parts) and fnmatchcase(parts[i], patterns[j]) and visit(i + 1, j + 1)

    return visit(0, 0)


def object_fields(value: object, allowed: set[str], required: set[str], label: str) -> dict:
    if not isinstance(value, dict):
        raise PolicyError(f"{label} must be an object")
    if set(value) - allowed or required - set(value):
        raise PolicyError(f"{label} has unknown or missing fields; see the version 2 policy reference")
    return value


def validate_budget(value: dict, label: str) -> None:
    maximum, warning = value["max_tokens"], value["warn_tokens"]
    if (type(maximum) is not int or type(warning) is not int
            or not 0 <= warning <= maximum or maximum == 0):
        raise PolicyError(f"{label} requires integer 0 <= warn_tokens <= max_tokens and max_tokens > 0")
    for key in ("warn_severity", "max_severity"):
        if value[key] not in ("warning", "error"):
            raise PolicyError(f"{label} severities must be warning or error")
    if value["warn_severity"] == "error" and value["max_severity"] != "error":
        raise PolicyError(f"{label} max_severity cannot be weaker than warn_severity")
    for key in DEFAULT_MESSAGES:
        if not isinstance(value[key], str) or not value[key].strip():
            raise PolicyError(f"{label} messages must be nonempty strings")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise PolicyError("policy has a duplicate JSON key; remove the duplicate")
        value[key] = item
    return value


def parse(raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PolicyError("policy must be valid UTF-8 JSON; validate its syntax locally") from error
    value = object_fields(value, {
        "version", "encoding", "include", "exclude", "defaults", "rules", "full_scan_on",
    }, {"version", "encoding", "include", "exclude", "defaults", "rules"}, "policy")
    if type(value["version"]) is not int or value["version"] != 2:
        raise PolicyError("unsupported policy version; expected 2 (migrate roots/files to include/rules)")
    if not isinstance(value["encoding"], str) or not value["encoding"].strip():
        raise PolicyError("encoding must name a tiktoken encoding")
    for key in ("include", "exclude", "rules", "full_scan_on"):
        if not isinstance(value.get(key, []), list):
            raise PolicyError(f"{key} must be an array")
    if not value["include"]:
        raise PolicyError("include must contain at least one glob")
    for glob in value["include"] + value.get("full_scan_on", []):
        pattern(glob)
    for exclusion in value["exclude"]:
        object_fields(exclusion, {"glob", "reason"}, {"glob", "reason"}, "exclusion")
        pattern(exclusion["glob"])
        require_reason(exclusion)
    defaults = object_fields(value["defaults"], BUDGET_FIELDS,
                             {"max_tokens", "warn_tokens"}, "defaults")
    defaults = {"warn_severity": "warning", "max_severity": "error", **DEFAULT_MESSAGES, **defaults}
    validate_budget(defaults, "defaults")
    value["defaults"] = defaults
    for rule in value["rules"]:
        object_fields(rule, BUDGET_FIELDS | {"glob", "reason"}, {"glob", "reason"}, "rule")
        pattern(rule["glob"])
        require_reason(rule)
        # Validate field types without assuming which earlier rules match a path.
        for key in BUDGET_FIELDS & rule.keys():
            candidate = {**defaults, key: rule[key]}
            if key == "max_tokens":
                candidate["warn_tokens"] = 0
            elif key == "warn_tokens":
                candidate["max_tokens"] = rule[key] if type(rule[key]) is int and rule[key] > 0 else defaults["max_tokens"]
            elif key == "warn_severity":
                candidate["max_severity"] = "error"
            elif key == "max_severity":
                candidate["warn_severity"] = "warning"
            validate_budget(candidate, "rule")
        if {"max_tokens", "warn_tokens"} <= rule.keys() and rule["warn_tokens"] > rule["max_tokens"]:
            raise PolicyError("rule warn_tokens must not exceed its explicit max_tokens")
        if rule.get("warn_severity") == "error" and rule.get("max_severity") == "warning":
            raise PolicyError("rule max_severity cannot be weaker than its explicit warn_severity")
    return value


def require_reason(value: dict) -> None:
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise PolicyError("every rule and exclusion requires a nonempty reason")


def select(path: str, policy: dict) -> tuple[dict | None, str]:
    for exclusion in policy["exclude"]:
        if matches(path, exclusion["glob"]):
            return None, exclusion["reason"]
    if not any(matches(path, glob) for glob in policy["include"]):
        return None, "Outside the explicit include globs"
    budget = dict(policy["defaults"])
    applied = []
    for rule in policy["rules"]:
        if matches(path, rule["glob"]):
            budget.update({key: rule[key] for key in BUDGET_FIELDS & rule.keys()})
            applied.append({"glob": rule["glob"], "reason": rule["reason"]})
    validate_budget(budget, f"effective budget for {display(path)}")
    budget["rules"] = applied
    return budget, ""
