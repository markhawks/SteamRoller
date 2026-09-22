#!/usr/bin/python3
"""Validate effective SteamRoller configuration without contacting targets."""

import argparse
import json
import subprocess
import sys


LIST_FIELDS = (
    "steamroller_allowed_repo_files",
    "steamroller_required_repositories",
    "steamroller_critical_services",
    "steamroller_application_services",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--environment-settings")
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args()
    command = [
        "ansible-inventory", "-i", args.inventory,
        "-e", f"@{args.settings}",
    ]
    if args.environment_settings:
        command.extend(["-e", f"@{args.environment_settings}"])
    command.extend(["-e", f"steamroller_report_root={args.report_root}", "--list"])
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        hostvars = json.loads(result.stdout).get("_meta", {}).get("hostvars", {})
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"CONFIG FAIL: unable to load effective configuration: {error}", file=sys.stderr)
        return 2

    if not hostvars:
        print("CONFIG FAIL: inventory contains no hosts", file=sys.stderr)
        return 2

    errors: list[str] = []
    defaults = {
        "steamroller_disk_warning_percent": 80,
        "steamroller_disk_critical_percent": 95,
        "steamroller_inode_warning_percent": 80,
        "steamroller_inode_failure_percent": 95,
        "steamroller_root_min_free_mb": 4096,
        "steamroller_boot_min_free_mb": 400,
        "steamroller_uptime_warning_days": 90,
        "steamroller_uptime_high_days": 180,
        "steamroller_uptime_critical_days": 365,
        "steamroller_custom_repo_policy": "fail",
        "steamroller_registration_mode": "auto",
    }
    for host, variables in hostvars.items():
        values = {key: variables.get(key, value) for key, value in defaults.items()}
        for key in (
            "steamroller_disk_warning_percent", "steamroller_disk_critical_percent",
            "steamroller_inode_warning_percent", "steamroller_inode_failure_percent",
        ):
            value = values[key]
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
                errors.append(f"{host}: {key} must be an integer from 0 to 100")
        if values["steamroller_disk_warning_percent"] >= values["steamroller_disk_critical_percent"]:
            errors.append(f"{host}: disk warning threshold must be lower than high-use threshold")
        if values["steamroller_inode_warning_percent"] >= values["steamroller_inode_failure_percent"]:
            errors.append(f"{host}: inode warning threshold must be lower than failure threshold")
        for key in ("steamroller_root_min_free_mb", "steamroller_boot_min_free_mb"):
            value = values[key]
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"{host}: {key} must be a positive integer")
        uptime = [
            values["steamroller_uptime_warning_days"],
            values["steamroller_uptime_high_days"],
            values["steamroller_uptime_critical_days"],
        ]
        if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in uptime):
            errors.append(f"{host}: uptime thresholds must be positive integers")
        elif not uptime[0] < uptime[1] < uptime[2]:
            errors.append(f"{host}: uptime thresholds must be strictly increasing")
        if values["steamroller_custom_repo_policy"] not in {"allow", "warning", "fail"}:
            errors.append(f"{host}: custom repository policy must be allow, warning, or fail")
        if values["steamroller_registration_mode"] not in {"auto", "redhat_cdn", "satellite"}:
            errors.append(
                f"{host}: registration mode must be auto, redhat_cdn, or satellite"
            )
        for key in LIST_FIELDS:
            if not isinstance(variables.get(key, []), list):
                errors.append(f"{host}: {key} must be a list")

    if errors:
        for error in errors:
            print(f"CONFIG FAIL: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
