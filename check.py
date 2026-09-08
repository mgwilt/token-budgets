# /// script
# requires-python = ">=3.11"
# dependencies = ["tiktoken==0.14.0"]
# ///
"""Read-only repository token budgets: uv run --script check.py --check."""

import sys

sys.dont_write_bytecode = True

from token_budgets.cli import main

if __name__ == "__main__":
    sys.exit(main())
