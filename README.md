# token-budgets

Per-file token budgets for code and documentation. Review structure; preserve content.

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

From your repository root, copy the [sample](examples/polyglot.json) (every setting):

```sh
git submodule add https://github.com/mgwilt/token-budgets.git tools/token-budgets
cp tools/token-budgets/examples/polyglot.json token-budgets.json
```

Illustrative limits:

| Example file | Warn / max tokens | Purpose |
| --- | --- | --- |
| `docs/architecture.md` | 1500 / 2000 | Markdown explanations |
| `docs/index.md` | 400 / 500 | Short navigation |
| `apps/web/src/checkout.ts` | 2000 / 2500 | TypeScript UI logic |
| `services/api/orders.py` | 2400 / 3000 | Python service logic |
| `crates/core/src/query.rs` | 2800 / 3500 | Rust implementation |
| `crates/core/src/lib.rs` | 600 / 800 | Public entrypoint; blocks at 600 |
| `docs/reference/protocol.md` | 1500 / 2000 | Cohesive reference; advisory findings |
| Other included files | 3000 / 4000 | Default budget |

## Policy concepts

| Setting | Meaning |
| --- | --- |
| `version`, `encoding` | Schema `2`; shared tokenizer across languages. |
| `include` | `**` covers every path, including new languages. |
| `exclude` | `{glob, reason}` entries omit dependencies, generated/binary files and submodules. First match wins. |
| `defaults`, `rules` | Budget, then all matching `{glob, reason, …}` rules in order. Later fields win; exclusions always win. |
| `warn_tokens`, `max_tokens` | Findings start **at** warning and **above** maximum. |
| `warn_severity`, `max_severity` | Only `error` blocks `--check`; `warning` is advisory. |
| `warn_message`, `max_message` | Custom review prompts; shared guidance remains. |
| `full_scan_on` | Staged matches check the whole index; policy/utility changes do this automatically. |

`docs/index.md` inherits defaults → Markdown → index overrides: 400/500 tokens.
Unmentioned fields stay inherited. [Globs and validation](docs/policy.md).

## Run checks

```sh
# Working tree: tracked and nonignored untracked files
uv run --script tools/token-budgets/check.py --check
# Exact staged policy and bytes
uv run --script tools/token-budgets/check.py --staged --check
```

Use `--staged --all --json` for full index reports. Checks never modify files or echo source. Commit policy and submodule together. Fresh clones: `git submodule update --init --recursive`.

[Checks, exit codes and hooks](docs/checks.md) · [Python API](docs/count.md) ·
[Architecture review](docs/review.md) · [Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md) · [MIT License](LICENSE)
