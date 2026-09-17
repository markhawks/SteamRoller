#!/usr/bin/python3
"""Display effective, non-sensitive SteamRoller check configuration."""

import argparse
import json
import subprocess
import sys


FIELDS = (
    ("Registration mode", "steamroller_registration_mode", "redhat_cdn"),
    ("Cluster check enabled", "steamroller_cluster_check_enabled", False),
    ("Report root", "steamroller_report_root", "reports"),
    ("Disk usage warning", "steamroller_disk_warning_percent", 80, "%"),
    ("Disk high-use warning", "steamroller_disk_critical_percent", 95, "%"),
    ("Root minimum free space", "steamroller_root_min_free_mb", 4096, " MiB"),
    ("Boot minimum free space", "steamroller_boot_min_free_mb", 400, " MiB"),
    ("Inode usage warning", "steamroller_inode_warning_percent", 80, "%"),
    ("Inode usage failure", "steamroller_inode_failure_percent", 95, "%"),
    ("Uptime warning threshold", "steamroller_uptime_warning_days", 90, " days"),
    ("Uptime high threshold", "steamroller_uptime_high_days", 180, " days"),
    ("Uptime critical threshold", "steamroller_uptime_critical_days", 365, " days"),
    ("Allowed repository files", "steamroller_allowed_repo_files", ["redhat.repo"]),
    ("Custom repository policy", "steamroller_custom_repo_policy", "fail"),
    ("Required repository IDs", "steamroller_required_repositories", []),
    ("Critical services", "steamroller_critical_services", []),
    ("Application services", "steamroller_application_services", []),
)


def display(value: object, suffix: str = "") -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return f"{value}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args()

    command = [
        "ansible-inventory",
        "-i",
        args.inventory,
        "-e",
        f"@{args.settings}",
        "-e",
        f"steamroller_report_root={args.report_root}",
        "--list",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        inventory = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"Unable to read effective configuration: {error}", file=sys.stderr)
        return 2

    hostvars = inventory.get("_meta", {}).get("hostvars", {})
    print("STEAMROLLER EFFECTIVE CONFIGURATION")
    print(f"Environment: {args.environment}")
    print(f"Managed OS policy: RHEL 9.x only")
    print(f"Inventory hosts: {len(hostvars)}")
    print()

    for field in FIELDS:
        label, key, default, *optional_suffix = field
        suffix = optional_suffix[0] if optional_suffix else ""
        values = {json.dumps(values.get(key, default), sort_keys=True) for values in hostvars.values()}
        if not values:
            effective: object = default
        elif len(values) == 1:
            effective = json.loads(values.pop())
        else:
            effective = "varies by host"
            suffix = ""
        print(f"{label:<30} {display(effective, suffix)}")

    print()
    print(f"Settings file: {args.settings}")
    print(f"Inventory file: {args.inventory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
