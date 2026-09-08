# Contributing

Bug reports, documentation improvements and focused pull requests are welcome.
Use the [issue tracker](https://github.com/mgwilt/token-budgets/issues) for questions
and reproducible bugs. Discuss substantial interface changes before implementing
them. See [SECURITY.md](SECURITY.md) before sharing sensitive information.

## Local setup

Install Python 3.11+, Git and [uv](https://docs.astral.sh/uv/), then clone the
repository using the [quick start](README.md#quick-start). The scripts declare
their pinned tokenizer dependency; no editable installation or external workspace
is required. First use needs access to dependency and public tokenizer downloads.

Run the complete local checks:

```sh
uv run --with tiktoken==0.14.0 python -m unittest discover -s tests -v
uv run --script check.py --all --check
git diff --check
```

Tests create temporary Git repositories and exercise the actual command-line
entrypoints. The repository has no hosted workflow; run these commands locally
before submitting changes and include their results in your pull request.

To verify staged execution after staging the intended changes:

```sh
uv run --script check.py --staged --all --check
```

The checker intentionally rejects staged runs when its execution files differ
from the index. Full working-tree checks remain available during development.

## Making a change

Keep a pull request focused on one behavior or documented need. Include a small
reproduction for bugs and describe the observable result of the fix. Add tests
for changed behavior and important failure paths, rather than duplicating the
implementation in assertions. Update the relevant command examples and reference
documentation when the interface changes.

Preserve full input bytes, exact staged-policy semantics, deterministic metadata
and the read-only contract. Do not add source excerpts to reports or use real
private content as fixtures. Explain narrow policy exceptions; a failing token
budget is a prompt to review cohesion, not permission to delete evidence or
compress code. There is no line-width requirement.

Use clear Conventional Commit messages, such as `fix: preserve staged policy
selection` or `docs: clarify raw count output`. State the commands you ran and
distinguish observed results from checks you could not perform.

## License

Contributions are provided under this repository's [MIT License](LICENSE).
Only submit material you have the right to contribute, and preserve relevant
third-party copyright and license notices.
