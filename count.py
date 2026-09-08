# /// script
# requires-python = ">=3.11"
# dependencies = ["tiktoken==0.14.0"]
# ///
"""Count raw stdin locally: uv run --script count.py < input.txt."""

import sys

sys.dont_write_bytecode = True

from token_budgets.count import main

if __name__ == "__main__":
    sys.exit(main())
