# Checks and integration

Run the utility from the repository being checked, or keep a separate clone and
pass the target with `uv run --script path/to/token-budgets/check.py --root path/to/repo --check`.
`--config` selects a policy path relative to that target repository.

## Snapshot contract

Full worktree checks inventory tracked paths plus nonignored untracked paths.
They read files as bytes, reject selected symlinks (including parent directories),
decode UTF-8 without newline normalization, and count the entire text with
`encode(text, disallowed_special=())`. Literal special-token-looking text is
accepted. UTF-8 failures and NUL-containing binary files need explicit exclusions.
Missing tracked working-tree files are read failures; staged deletions are absent
from the index and need no count.

Staged checks read `git ls-files --stage -z` and retrieve blobs by object ID.
NUL-separated names handle spaces, newlines and leading dashes without shell
interpolation. Unmerged index entries fail. An empty initial repository is
supported once its policy and content are staged. Partial staging does not change
the counted bytes or the staged policy. Index changes during a check fail and
request a fresh run. No check writes repository content, index, or Git objects.
Tokenizer setup may write dependency/encoding caches outside source content.

The policy path, `.gitmodules`, the executing utility path, and `full_scan_on`
patterns automatically trigger full index coverage when staged. Checker code in
a submodule must match the staged gitlink and have clean execution files. Git hook
environment variables are retained for the parent index, including temporary
commit indexes, and cleared when inspecting a submodule's own repository.
When the utility is developed directly in the checked repository, its execution
files must also match the index. Policy deletion or an unstaged-only policy fails; checks never fall back to
working-tree policy. Empty staged changes pass; an empty full selection fails.
Run full checks separately before review to cover remaining working-tree changes.

## Lefthook

Use an unfiltered job; filename interpolation is unnecessary and can skip policy
changes or deletion-only commits:

```yaml
no_auto_install: true
pre-commit:
  jobs:
    - name: token-budgets
      run: uv run --script tools/token-budgets/check.py --staged --check
      stage_fixed: false
```

Invoke with `lefthook run pre-commit --no-auto-install --no-stage-fixed --force`.
Lefthook 2.1.12 otherwise guards partially staged files by temporarily hiding
working-tree changes even when the job has `stage_fixed: false`. Install a hook
that uses these flags and preserves any existing hooks. Worktrees share default
hooks: use a per-worktree hook path when independent checkouts differ.

Hooks are local developer checks, not a security boundary: local hooks and their
configuration can be changed or skipped. CI should run the pinned utility's full
check independently. Review policy exceptions and changes to the checker itself.

## Output and validation

Use `--details all` for per-file counts and exclusion reasons, or `--json` for
structured metadata. JSON includes report/counting-policy/utility versions, tokenizer package and pin,
encoding, policy hash, scope, trigger paths, omissions with reasons, per-file byte
counts/hashes/token counts, effective thresholds and rules, guidance, summary and
the actual exit code. It has no timestamps, absolute root paths or source excerpts.
The same report drives human output and exit status. Paths are escaped for safe
terminal display. Findings without `--check` return 0; enforced error findings
return 1; malformed policies and read/setup failures return 2.

```sh
uv run --with tiktoken==0.14.0 python -m unittest discover -s tests -v
uv run --script check.py --all --check
```

Tests exercise boundaries, severity, Unicode/CRLF/special text, deterministic
metadata, read-only behavior, malformed inputs, exact staged bytes and policy,
names, deletion/rename, full-scan triggers, symlinks, and cached offline counting.

Primary references: [tiktoken](https://github.com/openai/tiktoken),
[encoding implementation](https://github.com/openai/tiktoken/blob/main/tiktoken/core.py),
[Lefthook staging guard](https://github.com/evilmartians/lefthook/blob/v2.1.12/internal/run/controller/guard.go),
[Lefthook file filtering](https://lefthook.dev/configuration/glob.html).
