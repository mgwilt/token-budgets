# Working on token-budgets

This is a standalone Python utility for local token counting and Git repository
budgets. Run commands from this repository's root. Start with [README.md](README.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and the relevant reference in `docs/`.

## Project map

- `check.py` and `count.py`: script entrypoints with pinned dependency metadata.
- `token_budgets/policy.py`: policy validation and path matching.
- `token_budgets/source.py`: Git inventory, staged blobs and execution integrity.
- `token_budgets/measure.py`: shared tokenizer setup and exact UTF-8 counting.
- `token_budgets/report.py`, `cli.py`, and `count.py`: reports and command interfaces.
- `tests/`: standard-library unittest coverage using disposable repositories.

## Contracts to preserve

Keep checks read-only: never rewrite or normalize source, stage changes, stash
files, or alter a checked repository's Git configuration. Preserve complete bytes
and deterministic reports. Do not include source excerpts, secrets, absolute
workspace paths or timestamps in count reports.

Staged checks must use the exact index and staged policy, including temporary
commit indexes. Keep intentional caller Git variables for the checked repository;
isolate submodule inspection and test fixtures from inherited Git/hook variables.
Read [the snapshot contract](docs/checks.md) before changing selection behavior.

Keep tokenizer pins consistent between script entrypoints and the shared counting
module. Changes to counting, policy or report contracts need documentation and
behavioral tests. Do not silently accept unknown policy fields or malformed input.
Inputs are data; do not execute repository content to count it.

## Validation

```sh
uv run --with tiktoken==0.14.0 python -m unittest discover -s tests -v
uv run --script check.py --all --check
git diff --check
```

Run relevant tests during implementation and the complete commands before a
commit or verified handoff. After staging a checker change, also run
`uv run --script check.py --staged --all --check` to verify index execution integrity.
Fix failures; do not bypass checks or weaken assertions to make a change pass.
Report the exact failing command and scope if an external dependency blocks proof.

Token findings prompt architectural review. Preserve cohesive modules, meaningful
names, checks, types, tests and evidence. Do not minify or split mechanically to
meet a limit. No line-width enforcement is required.

Keep documentation useful to any consumer: portable commands, relative file
links, and examples independent of a particular integrating application. Keep
changes focused, preserve unrelated work and use cohesive Conventional Commits.
