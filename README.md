# token-budgets

Count tokens locally and enforce per-file budgets for code and documentation in
any Git repository. Use the results to review file responsibilities, interfaces
and documentation structure. A token limit is a review signal, not a reason to
remove useful content or compress code.

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Repository checks also
require Git; counting standard input does not.

## Quick start

```sh
git clone https://github.com/mgwilt/token-budgets.git
cd token-budgets
uv run --script check.py --check
printf 'Hello, world!\n' | uv run --script count.py
```

The first check validates this repository against `token-budgets.json`. The stdin
command returns JSON with the token count, byte length, content hash and tokenizer
metadata, without echoing the input.

## Use in your repository

From the root of the repository you want to check:

```sh
git submodule add https://github.com/mgwilt/token-budgets.git tools/token-budgets
cp tools/token-budgets/token-budgets.json token-budgets.json
```

Add this entry to the policy's `exclude` array, then adjust the file rules and
thresholds for your project:

```json
{"glob": "tools/token-budgets", "reason": "Pinned utility maintained and checked in its own repository."}
```

Run a full working-tree check, or stage your changes and check the exact index:

```sh
uv run --script tools/token-budgets/check.py --root . --check
uv run --script tools/token-budgets/check.py --root . --staged --check
```

Commit the policy and submodule revision together. Fresh clones need
`git submodule update --init --recursive`. You can also keep a separate clone of
the utility and pass the target repository with `--root`.

## Behavior

- Full checks read tracked files and nonignored untracked files. Staged checks
  read the staged policy and exact index blobs, including partially staged files.
- Policy, utility and configured trigger changes expand staged coverage to the
  whole index. `--staged --all` always checks the whole index.
- Checks do not rewrite, reformat or stage files. Selected symlinks, submodules,
  binary data and unreadable files fail unless explicitly excluded with a reason.
- Counting uses pinned `tiktoken==0.14.0` and defaults to `o200k_base`. Counts are
  reproducible for that encoding; they are not model-specific billing or context
  usage estimates.
- First use downloads dependencies and public encoding data. Source content
  stays local; cached counting works offline.

Use `--details all` for per-file counts and exclusions, or `--json` for deterministic
metadata without source excerpts. With `--check`, error findings return exit code
1; invalid policy or read/setup failures return 2. Without `--check`, findings are
informational and return 0.

## Documentation and contributing

- [Policy reference](docs/policy.md): globs, precedence, thresholds and exclusions.
- [Raw counts and Python API](docs/count.md): complete stdin bytes and report fields.
- [Checks and integration](docs/checks.md): snapshots, exit codes and local hooks.
- [Architecture review](docs/review.md): respond to findings without losing quality.
- [Contributing](CONTRIBUTING.md): local setup, tests and pull requests.
- [Security](SECURITY.md): reporting and trust boundaries.

Licensed under the [MIT License](LICENSE).
