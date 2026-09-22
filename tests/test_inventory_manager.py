#!/usr/bin/python3
"""Tests for the SteamRoller inventory manager."""

import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import manage_inventory


class InventoryManagerTest(unittest.TestCase):
    def test_resolve_host_extracts_address_from_ping(self) -> None:
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="PING server01.example.net (192.0.2.15) 56(84) bytes of data.\n",
            stderr="",
        )
        with patch.object(subprocess, "run", return_value=result):
            self.assertEqual(
                manage_inventory.resolve_host("server01.example.net"), "192.0.2.15"
            )

    def test_create_is_atomic_when_resolution_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            create = argparse.Namespace(
                command="create",
                inventory="BrokenLab",
                host=["server01", "missing-server"],
                port=22,
                user="root",
            )
            with patch.object(
                manage_inventory,
                "resolve_all",
                side_effect=manage_inventory.InventoryError("Host does not answer ping"),
            ):
                with self.assertRaises(manage_inventory.InventoryError):
                    manage_inventory.create_or_add(create, root)
            self.assertFalse((root / "BrokenLab" / "hosts.yml").exists())

    def test_create_add_list_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            create = argparse.Namespace(
                command="create",
                inventory="TestLab",
                host=["server01", "server02"],
                port=22,
                user="root",
            )
            with patch.object(
                manage_inventory,
                "resolve_all",
                return_value={"server01": "192.0.2.1", "server02": "192.0.2.2"},
            ):
                manage_inventory.create_or_add(create, root)

            inventory = root / "TestLab" / "hosts.yml"
            data = manage_inventory.load_inventory(inventory, "TestLab")
            hosts = manage_inventory.hosts_mapping(data, "TestLab")
            self.assertEqual(hosts["server01"]["ansible_host"], "192.0.2.1")
            self.assertEqual(hosts["server01"]["ansible_user"], "root")
            self.assertEqual(hosts["server01"]["ansible_port"], 22)

            add = argparse.Namespace(
                command="add",
                inventory="TestLab",
                host=["server03"],
                port=2222,
                user="operator",
            )
            with patch.object(
                manage_inventory,
                "resolve_all",
                return_value={"server03": "192.0.2.3"},
            ):
                manage_inventory.create_or_add(add, root)

            output = io.StringIO()
            with redirect_stdout(output):
                manage_inventory.list_hosts(root, "TestLab")
            self.assertIn("server03", output.getvalue())
            self.assertIn("192.0.2.3", output.getvalue())

            delete = argparse.Namespace(inventory="TestLab", host=["server01", "server03"])
            manage_inventory.delete_hosts(delete, root)
            remaining = manage_inventory.hosts_mapping(
                manage_inventory.load_inventory(inventory, "TestLab"), "TestLab"
            )
            self.assertEqual(list(remaining), ["server02"])

            subprocess.run(
                ["ansible-inventory", "-i", str(inventory), "--list"],
                check=True,
                capture_output=True,
                text=True,
            )


if __name__ == "__main__":
    unittest.main()
