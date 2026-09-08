# token-budgets

Count tokens locally and set per-file budgets for code and documentation. Rules
assign different limits by path. Findings prompt structural review; preserve
useful code and evidence.

Requires Python 3.11+, Git and [uv](https://docs.astral.sh/uv/).

## Quick start

```sh
git clone https://github.com/mgwilt/token-budgets.git
cd token-budgets
uv run --script check.py --check
printf 'Hello, world!\n' | uv run --script count.py
```

Pinned `tiktoken==0.14.0`/`o200k_base` counts are not billing estimates. Source stays
local; cached counting works offline after dependency/encoding downloads.

## Polyglot monorepo example

From your repository root:

```sh
git submodule add https://github.com/mgwilt/token-budgets.git tools/token-budgets
cp tools/token-budgets/examples/polyglot.json token-budgets.json
```

This complete `token-budgets.json` covers Markdown, TypeScript, Python and Rust.
It is identical to the [downloadable sample](examples/polyglot.json). Limits are
illustrative; choose them through architectural review.

```json
{
  "version": 2,
  "encoding": "o200k_base",
  "include": ["**"],
  "exclude": [
    {
      "glob": "tools/token-budgets",
      "reason": "Pinned utility submodule maintained and checked in its own repository."
    },
    {
      "glob": "vendor/**",
      "reason": "Third-party sources maintained upstream."
    },
    {
      "glob": "**/node_modules/**",
      "reason": "Installed JavaScript dependencies maintained upstream."
    },
    {
      "glob": "**/.venv/**",
      "reason": "Installed Python dependencies maintained upstream."
    },
    {
      "glob": "**/__pycache__/**",
      "reason": "Generated Python bytecode cache."
    },
    {
      "glob": "**/*.pyc",
      "reason": "Generated binary Python bytecode."
    },
    {
      "glob": "**/dist/**",
      "reason": "Generated application bundles; review their source files instead."
    },
    {
      "glob": "**/target/**",
      "reason": "Generated Rust compiler output; review crate sources instead."
    },
    {
      "glob": "**/generated/**",
      "reason": "Generated clients and bindings; review their schemas and generators instead."
    },
    {
      "glob": "assets/**/*.png",
      "reason": "Binary image assets reviewed visually rather than tokenized."
    }
  ],
  "defaults": {
    "max_tokens": 4000,
    "warn_tokens": 3000,
    "warn_severity": "warning",
    "max_severity": "error",
    "warn_message": "Review this file's responsibilities, interfaces and tests.",
    "max_message": "Resolve the architectural finding without removing useful code or evidence."
  },
  "rules": [
    {
      "glob": "**/*.md",
      "reason": "Keep explanations independently useful and discoverable.",
      "max_tokens": 2000,
      "warn_tokens": 1500,
      "warn_message": "Review navigation and the scope of this explanation.",
      "max_message": "Preserve evidence and link cohesive explanations where useful."
    },
    {
      "glob": "**/index.md",
      "reason": "Keep navigation short; linked documents retain the full detail.",
      "max_tokens": 500,
      "warn_tokens": 400
    },
    {
      "glob": "apps/web/**/*.ts",
      "reason": "Review UI state and effects as focused TypeScript modules.",
      "max_tokens": 2500,
      "warn_tokens": 2000
    },
    {
      "glob": "services/**/*.py",
      "reason": "Keep Python service modules focused on cohesive operations.",
      "max_tokens": 3000,
      "warn_tokens": 2400
    },
    {
      "glob": "crates/**/*.rs",
      "reason": "Review Rust module responsibilities and public interfaces.",
      "max_tokens": 3500,
      "warn_tokens": 2800
    },
    {
      "glob": "crates/core/src/lib.rs",
      "reason": "Review public entrypoint growth early; implementation belongs in cohesive modules.",
      "max_tokens": 800,
      "warn_tokens": 600,
      "warn_severity": "error"
    },
    {
      "glob": "docs/reference/**",
      "reason": "Retain complete protocol references linked from docs/index.md; findings remain review prompts as the protocol evolves.",
      "max_severity": "warning"
    }
  ],
  "full_scan_on": ["lefthook.yml", "scripts/check-tokens.sh"]
}
```

## How globs match

A glob is a path pattern, relative to the repository root. Matching is
case-sensitive, uses `/`, and includes dotfiles within Git's inventory.

| Glob | Matches | Does not match |
| --- | --- | --- |
| `docs/*.md` | `docs/index.md` | `docs/api/index.md` |
| `docs/**/*.md` | `docs/index.md`, `docs/api/index.md` | `docs/index.txt` |
| `**/*.md` | `README.md`, `docs/api/index.md` | `docs/api/schema.json` |
| `src/test?.py` | `src/test1.py` | `src/test10.py` |
| `src/*.[ch]` | `src/main.c`, `src/main.h` | `src/main.cpp` |
| `docs/index.md` | That exact path | `nested/docs/index.md` |

`*` matches zero or more characters; `?` matches one; `[ch]` matches one `c` or `h`.
None crosses `/`. `**` occupies a whole segment and matches zero or more segments.
There is no brace expansion: use separate `**/*.ts` and `**/*.tsx` patterns.

## How rules apply

A rule matches paths and overrides budget fields; it does not inspect language
syntax. Every matching rule applies **in list order, field by field**.

For `docs/index.md`, the sample produces:

| Step | Warn tokens | Max tokens |
| --- | --- | --- |
| `defaults` | 3000 | 4000 |
| `**/*.md` | 1500 | 2000 |
| `**/index.md` | 400 | 500 |

The index rule keeps the Markdown messages and inherited warning/error severities.
At 400 tokens it warns; at 500 it still warns; at 501 it blocks `--check`.

- `crates/core/src/lib.rs` matches the Rust rule, then the exact-path rule: its
  `warn_severity: "error"` blocks at 600 tokens.
- `docs/reference/protocol.md` matches Markdown, then the reference rule:
  `max_severity: "warning"` makes even an over-budget finding advisory.
- `vendor/guide.md` stays excluded despite matching `**/*.md`. Rules cannot
  reinclude an excluded file. Every rule and exclusion records a `reason`.

## Settings at a glance

| Setting | Meaning |
| --- | --- |
| `version`, `encoding` | Schema `2`; one tokenizer encoding across languages. |
| `include` | Eligible path globs; `**` also covers newly added languages. |
| `exclude` | Reasoned omissions; the first matching exclusion wins. Submodules match their exact gitlink path. |
| `defaults` | Starting per-file budget, not a repository-wide total. |
| `rules` | Ordered overrides; unmentioned fields stay inherited. |
| `warn_tokens`, `max_tokens` | Findings start **at** warning and **above** maximum. |
| `warn_severity`, `max_severity` | `warning` is advisory; `error` blocks `--check`. |
| `warn_message`, `max_message` | Custom review prompts alongside shared architecture guidance. |
| `full_scan_on` | Staged matches check the whole index; policy/utility changes already do this automatically. |

## Run checks

```sh
# Working tree: tracked and nonignored untracked files
uv run --script tools/token-budgets/check.py --check
# Exact staged policy and bytes
uv run --script tools/token-budgets/check.py --staged --check
```

Use `--staged --all --json` for full index reports. Checks never modify files or
echo source. Commit policy and submodule together. Fresh clones need
`git submodule update --init --recursive`.

[Policy reference](docs/policy.md) · [Checks and hooks](docs/checks.md) ·
[Python API](docs/count.md) · [Architecture review](docs/review.md) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT License](LICENSE)
