# token-budgets

Read-only, local token budgets for code and documentation in Git repositories.
Requires Python 3.11+, Git, and [uv](https://docs.astral.sh/uv/).

```sh
uv run --script check.py --root . --config token-budgets.json --check
uv run --script check.py --root . --config token-budgets.json --staged --check
uv run --script check.py --root . --config token-budgets.json --staged --all --check --json
```

The default full check reads tracked working-tree files and untracked files that
Git does not ignore. A staged check reads the staged policy and exact index blobs.
Policy, utility, or configured trigger changes expand it to the whole index.
`--staged --all` always checks the whole index. Nothing is staged, rewritten, or
reformatted. Selected symlinks, submodules, binary data, and unreadable files fail
with an actionable diagnostic unless explicitly excluded.

Count complete UTF-8 bytes with `tiktoken==0.14.0` and the configured encoding.
The default policy uses `o200k_base`; this is a reproducible repository signal,
not an exact Codex internal count. The first run downloads dependencies and
public encoding data. Source content stays local; cached counting works offline.

## Reuse

```sh
git submodule add https://github.com/mgwilt/token-budgets.git tools/token-budgets
cp tools/token-budgets/token-budgets.json token-budgets.json
uv run --script tools/token-budgets/check.py --root . --check
```

This repository is private; collaborators and CI need read access. Add a justified
exclusion for the submodule gitlink and configure your project's docs/code rules.
Commit the policy and pin the submodule revision. On a fresh clone, run
`git submodule update --init --recursive`.

- [Policy reference](docs/policy.md): globs, precedence, thresholds and exclusions.
- [Checks and integration](docs/checks.md): snapshots, exit codes, hooks and tests.
- [Architecture review](docs/review.md): acting on the signal without losing quality.

Human diagnostics show findings and architecture guidance. Use `--details all`
for counts, hashes and exclusions, or `--json` for deterministic metadata without
source excerpts. `--format human|json` is also supported. `--check` returns 1 for
error-severity findings; malformed policy and read/setup errors always return 2.
Without `--check`, findings are informational and return 0.
