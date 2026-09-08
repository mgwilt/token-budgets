# JSON policy version 2

Start with the [complete polyglot sample](../examples/polyglot.json) or this
repository's [own policy](../token-budgets.json). Required fields are `version`,
`encoding`, `include`, `exclude`, `defaults`, and `rules`. `full_scan_on` is optional.
Unknown fields, duplicate JSON keys, invalid types, or invalid effective thresholds
fail. Version 1 `roots`/`files` policies must be migrated explicitly.

```json
{
  "version": 2,
  "encoding": "o200k_base",
  "include": ["**"],
  "exclude": [
    {"glob": "vendor/**", "reason": "Third-party code maintained upstream."},
    {"glob": "tools/token-budgets", "reason": "Pinned utility; checked in its own repository."},
    {"glob": "build/**", "reason": "Generated build output."},
    {"glob": "assets/**/*.png", "reason": "Binary image assets."}
  ],
  "defaults": {
    "max_tokens": 4000,
    "warn_tokens": 3000,
    "warn_severity": "warning",
    "max_severity": "error",
    "warn_message": "Review this file's responsibilities and cohesive boundaries.",
    "max_message": "Review architecture; record a justified resolution before committing."
  },
  "rules": [
    {"glob": "**/*.md", "reason": "Bound explanatory leaves.", "max_tokens": 2000, "warn_tokens": 1500},
    {"glob": "**/index.md", "reason": "Keep discovery shallow.", "max_tokens": 500, "warn_tokens": 400}
  ],
  "full_scan_on": ["scripts/check_tokens.py", "lefthook.yml"]
}
```

## Selection and precedence

Paths are case-sensitive, repository-relative, use `/`, and include dotfiles.
`*`, `?`, and `[abc]` match inside one segment. `**` occupies a whole segment and
matches zero or more segments, so `**/*.md` includes root Markdown files.
No brace expansion, negation, absolute paths, or `..` segments are supported.

1. The first matching exclusion wins, even if a later include/rule matches.
2. At least one include glob must match. Nonmatching paths appear in the report
   as outside explicit includes. Prefer `include: ["**"]` to catch new languages.
3. Start from `defaults`, then apply every matching rule in list order. The last
   matching value for each field wins; unmentioned fields retain earlier values.

Every exclusion and rule needs a nonempty `reason`. All inventory omissions are
listed in JSON and `--details all`; human output always shows their count.
Git-ignored **untracked** files lie outside Git's source inventory. Tracked files
remain covered even if ignored. Use explicit exclusions for vendor, generated,
build and binary content so forced/tracked additions also have a visible policy.
Submodules are gitlinks; this utility does not recursively inspect them. Exclude
each with its ownership reason and run its own check independently.

## Thresholds and messages

Defaults require integer `max_tokens > 0` and `0 <= warn_tokens <= max_tokens`.
Rules may override any threshold, severity or message. Effective budgets are
validated for all included inventory paths, even during a staged-only run.

| Count | Status | Severity/message |
| --- | --- | --- |
| Below warning | `ok` | No finding |
| At warning through maximum, inclusive | `warning` | `warn_severity` / `warn_message` |
| Above maximum | `over` | `max_severity` / `max_message` |

Severities are `warning` or `error`. Defaults are warning/error. Maximum severity
cannot be weaker than warning severity. Messages default to concrete review
prompts and may be customized; shared architecture guidance is always retained.
Only error-severity findings block `--check`; input failures always block.

An archive exclusion or larger per-file limit should name why retention/cohesion
matters and how readers discover and retrieve the content. Token size alone does
not justify splitting or relaxing a limit. Revisit exceptions with architecture
changes; do not silently exempt an oversized file.
