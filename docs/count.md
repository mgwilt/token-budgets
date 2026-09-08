# Raw stdin and Python counts

```sh
uv run --script count.py < input.txt
uv run --script tools/token-budgets/count.py --encoding o200k_base < input.txt
```

The command reads stdin through EOF and emits one JSON object. It needs no Git
repository or policy and performs no directory scan. `--json` is accepted for
compatibility; JSON is always the output format. Argument errors also return JSON.

Input is the complete raw UTF-8 byte stream: no truncation, stripping, newline
conversion, or normalization. Empty input is valid and counts as zero tokens.
Unicode, CRLF, NUL characters, and special-token-looking text are accepted
literally. Repository checks retain their separate NUL/binary-content restriction.
The tokenizer pin, encoding setup, and exact counting algorithm are shared with
the repository checker. The default `o200k_base` count is a reproducible policy
signal, not a model-specific billing or context usage estimate.

## Python API

With the utility on the Python import path and its pinned dependency installed:

```python
from token_budgets.count import count_bytes

report = count_bytes(b"Complete UTF-8 input\r\n", encoding_name="o200k_base")
assert report["exit_code"] == 0
tokens = report["tokens"]
```

`count_bytes(raw: bytes, encoding_name: str = "o200k_base") -> dict` returns the
same report as the CLI. Reports contain no source text or timestamps:

| Fields | Meaning |
| --- | --- |
| `report_version`, `counting_policy_version` | Both are `1` for this API. |
| `utility_version` | Utility release version. |
| `encoding`, `encoding_purpose` | Selected encoding and repository-policy caveat. |
| `tokenizer` | Package, observed version, and required version (`0.14.0`). |
| `tokens`, `bytes`, `sha256` | Count, raw byte length, and hash of the entire input. |
| `errors`, `exit_code` | Empty errors and `0` on success; safe errors and `2` on failure. |

Invalid UTF-8, read failures, and tokenizer failures produce metadata-only error
reports with `tokens: null`. Byte length and hash remain available whenever the
complete bytes were read; they are null on a read failure. The tokenizer's observed
version is null until setup discovers it. The CLI does not print input/setup error
details to stderr or include source excerpts in its JSON.

First use may download the pinned dependency and public encoding data. Input stays
local and is never uploaded. Once cached, both CLI and API work offline; cache
setup may write outside the input source. Preserve the original input when
counting fails and correct the encoding or dependency setup before retrying.
