#!/usr/bin/python3
"""Tests for managed SSH private-key discovery."""

from pathlib import Path
import tempfile
import unittest

from scripts import resolve_ssh_key


class SshKeyResolverTest(unittest.TestCase):
    @staticmethod
    def make_key(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "-----BEGIN OPENSSH PRIVATE KEY-----\ntest-fixture\n",
            encoding="utf-8",
        )

    def test_automatically_selects_only_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            key = root / "foreman" / "id_rsa"
            self.make_key(key)
            self.assertEqual(resolve_ssh_key.resolve(root, None), key.resolve())

    def test_profile_selects_key_inside_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            key = root / "foreman" / "id_ed25519"
            self.make_key(key)
            self.make_key(root / "production" / "id_rsa")
            self.assertEqual(resolve_ssh_key.resolve(root, "foreman"), key.resolve())

    def test_multiple_keys_require_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_key(root / "foreman" / "id_rsa")
            self.make_key(root / "production" / "id_rsa")
            with self.assertRaises(ValueError):
                resolve_ssh_key.resolve(root, None)


if __name__ == "__main__":
    unittest.main()
