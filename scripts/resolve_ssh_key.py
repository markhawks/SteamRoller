#!/usr/bin/python3
"""Resolve a SteamRoller SSH private key without exposing key contents."""

import argparse
from pathlib import Path
import sys


PRIVATE_KEY_MARKERS = (
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN DSA PRIVATE KEY-----",
    b"-----BEGIN PRIVATE KEY-----",
)


def is_private_key(path: Path) -> bool:
    if not path.is_file() or path.name.endswith(".pub"):
        return False
    try:
        with path.open("rb") as stream:
            first_bytes = stream.read(128)
    except OSError:
        return False
    return any(marker in first_bytes for marker in PRIVATE_KEY_MARKERS)


def keys_in(directory: Path, recursive: bool) -> list[Path]:
    if not directory.is_dir():
        return []
    paths = directory.glob("*/*") if recursive else directory.glob("*")
    return sorted((path.resolve() for path in paths if is_private_key(path)), key=str)


def resolve(key_root: Path, selector: str | None) -> Path | None:
    if selector:
        selected = Path(selector).expanduser()
        if not selected.exists():
            selected = key_root / selector
        if selected.is_file():
            if not is_private_key(selected):
                raise ValueError(f"not a recognized private key: {selected}")
            return selected.resolve()
        if not selected.is_dir():
            raise ValueError(f"SSH key file or profile does not exist: {selector}")
        candidates = keys_in(selected, recursive=False)
        if not candidates:
            raise ValueError(f"no private key found in profile: {selected}")
        if len(candidates) > 1:
            names = ", ".join(path.name for path in candidates)
            raise ValueError(f"multiple private keys in profile {selected}: {names}")
        return candidates[0]

    candidates = keys_in(key_root, recursive=True)
    candidates.extend(keys_in(key_root, recursive=False))
    candidates = sorted(set(candidates), key=str)
    if not candidates:
        return None
    if len(candidates) > 1:
        profiles = ", ".join(
            str(path.parent.relative_to(key_root)) if path.parent != key_root else path.name
            for path in candidates
        )
        raise ValueError(
            f"multiple managed SSH keys found ({profiles}); select one with -sk PROFILE"
        )
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-root", required=True)
    parser.add_argument("--selector")
    args = parser.parse_args()
    try:
        result = resolve(Path(args.key_root), args.selector)
    except ValueError as error:
        print(f"SSH KEY FAIL: {error}", file=sys.stderr)
        return 2
    if result:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
