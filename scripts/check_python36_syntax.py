#!/usr/bin/python3
"""Check project Python sources against the Python 3.6 grammar."""

import ast
from pathlib import Path
import sys


def main():
    paths = list(Path("scripts").glob("*.py")) + list(Path("tests").glob("*.py"))
    options = {"feature_version": 6} if sys.version_info >= (3, 8) else {}
    for path in paths:
        ast.parse(path.read_text(), filename=str(path), **options)
    print("Python 3.6 grammar check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
