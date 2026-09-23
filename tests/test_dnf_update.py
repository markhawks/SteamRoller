#!/usr/bin/python3
"""Focused unit tests for the interactive DNF update coordinator."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_dnf_update.py"
SPEC = importlib.util.spec_from_file_location("run_dnf_update", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DnfUpdateHelpersTest(unittest.TestCase):
    def test_ssh_command_uses_inventory_connection_values(self) -> None:
        command = MODULE.ssh_base(
            "node-a.example",
            {"ansible_host": "192.0.2.10", "ansible_user": "ops", "ansible_port": 2222},
            "/secure/update-key",
        )
        self.assertEqual(command[-1], "ops@192.0.2.10")
        self.assertIn("2222", command)
        self.assertIn("/secure/update-key", command)

    def test_non_root_remote_commands_require_non_interactive_sudo(self) -> None:
        self.assertEqual(
            MODULE.privileged("dnf upgrade", {"ansible_user": "ops"}),
            "sudo -n dnf upgrade",
        )
        self.assertEqual(
            MODULE.privileged("dnf upgrade", {"ansible_user": "root"}),
            "dnf upgrade",
        )

    def test_systemd_service_name_is_extracted(self) -> None:
        self.assertEqual(
            MODULE.service_name("● example.service loaded failed failed Example"),
            "example.service",
        )


if __name__ == "__main__":
    unittest.main()
