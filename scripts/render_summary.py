#!/usr/bin/python3
"""Render one SteamRoller run as an operator-oriented fleet summary."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


class Palette:
    def __init__(self) -> None:
        enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        self.red = "\033[1;31m" if enabled else ""
        self.yellow = "\033[1;33m" if enabled else ""
        self.green = "\033[1;32m" if enabled else ""
        self.bold = "\033[1m" if enabled else ""
        self.reset = "\033[0m" if enabled else ""

    def status(self, value: str) -> str:
        if value == "PASS":
            color = self.green
        elif value in {"WARNING", "SUCCESS WITH WARNINGS"}:
            color = self.yellow
        else:
            color = self.red
        return f"{color}{value}{self.reset}"


def expected_hosts(inventory: str) -> list[str]:
    try:
        result = subprocess.run(
            ["ansible-inventory", "-i", inventory, "--list"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        return sorted(data.get("_meta", {}).get("hostvars", {}).keys())
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def read_connectivity(path: Path) -> dict[str, object]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return {
        "host": values.get("HOST", path.parent.parent.name),
        "fqdn": values.get("SERVER_NAME", path.parent.parent.name),
        "status": values.get("RESULT", "FAIL"),
        "os": {},
        "kernel": {},
        "updates": {},
        "warnings": [],
        "failures": [] if values.get("RESULT") == "PASS" else ["Connectivity validation failed"],
        "duration_seconds": "-",
        "report_dir": str(path.parent),
    }


def load_rows(report_root: Path, run_id: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(report_root.glob(f"*/{run_id}/summary.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            row["report_dir"] = str(path.parent)
            rows.append(row)
        except (OSError, json.JSONDecodeError) as error:
            rows.append(
                {
                    "host": path.parent.parent.name,
                    "fqdn": path.parent.parent.name,
                    "status": "FAIL",
                    "failures": [f"Invalid summary.json: {error}"],
                    "warnings": [],
                    "report_dir": str(path.parent),
                }
            )
    if not rows:
        for path in sorted(report_root.glob(f"*/{run_id}/connectivity.txt")):
            rows.append(read_connectivity(path))
    return rows


def text(value: object, maximum: int) -> str:
    rendered = str(value if value not in (None, "") else "-")
    return rendered if len(rendered) <= maximum else rendered[: maximum - 1] + "…"


def service_name(line: object) -> str:
    """Extract a systemd unit name from systemctl --failed output."""
    fields = str(line).strip().lstrip("●").strip().split()
    return fields[0] if fields else "unknown-service"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--environment", required=True)
    args = parser.parse_args()

    palette = Palette()
    report_root = Path(args.report_root)
    rows = load_rows(report_root, args.run_id)
    present_hosts = {str(row.get("host", "")) for row in rows}
    for host in expected_hosts(args.inventory):
        if host not in present_hosts:
            rows.append(
                {
                    "host": host,
                    "fqdn": host,
                    "status": "FAIL",
                    "failures": ["No report produced; inspect the Ansible execution error"],
                    "warnings": [],
                    "report_dir": "-",
                }
            )
    rows.sort(key=lambda row: str(row.get("host", "")))

    print()
    print(f"{palette.bold}STEAMROLLER RUN SUMMARY{palette.reset}")
    print(f"Run: {args.run_id}    Environment: {args.environment}    Hosts: {len(rows)}")
    print()
    headers = ("SERVER", "RESULT", "RHEL", "RUNNING KERNEL", "NEXT KERNEL", "UPDATES", "WARN", "FAIL", "SECONDS")
    widths = (20, 10, 8, 30, 30, 9, 6, 6, 8)
    print(" ".join(f"{header:<{width}}" for header, width in zip(headers, widths)))
    print(" ".join("-" * width for width in widths))

    failed = 0
    warned = 0
    for row in rows:
        status = str(row.get("status", "FAIL"))
        failures = list(row.get("failures", []) or [])
        warnings = list(row.get("warnings", []) or [])
        os_data = row.get("os", {}) or {}
        kernel_data = row.get("kernel", {}) or {}
        updates = row.get("updates", {}) or {}
        if status == "FAIL" or failures:
            failed += 1
        elif status == "WARNING" or warnings:
            warned += 1
        values = (
            text(row.get("fqdn") or row.get("host"), widths[0]),
            palette.status(status),
            text(os_data.get("version", "-"), widths[2]),
            text(kernel_data.get("running", "-"), widths[3]),
            text(kernel_data.get("planned", "-"), widths[4]),
            text(updates.get("total", "-"), widths[5]),
            str(len(warnings)),
            str(len(failures)),
            text(row.get("duration_seconds", "-"), widths[8]),
        )
        # Status contains optional terminal color sequences, so pad its raw value first.
        display = [f"{values[0]:<{widths[0]}}", f"{palette.status(status):<{widths[1] + len(palette.status(status)) - len(status)}}"]
        display.extend(f"{value:<{width}}" for value, width in zip(values[2:], widths[2:]))
        print(" ".join(display))

    for row in rows:
        failures = list(row.get("failures", []) or [])
        warnings = list(row.get("warnings", []) or [])
        if not failures and not warnings:
            continue
        server = row.get("fqdn") or row.get("host")
        print()
        print(f"{palette.bold}{server}{palette.reset}")
        for finding in failures:
            print(f"  {palette.red}[FAIL]{palette.reset} {finding}")
        for finding in warnings:
            print(f"  {palette.yellow}[WARNING]{palette.reset} {finding}")

    detailed_rows = [row for row in rows if row.get("os") or row.get("disk_space")]
    if detailed_rows:
        print()
        print(f"{palette.bold}HOST DETAILS{palette.reset}")
        for row in detailed_rows:
            server = row.get("fqdn") or row.get("host")
            status = str(row.get("status", "FAIL"))
            os_data = row.get("os", {}) or {}
            kernel = row.get("kernel", {}) or {}
            updates = row.get("updates", {}) or {}
            disk_space = row.get("disk_space", {}) or {}
            filesystems = row.get("filesystems", []) or []
            inode_thresholds = row.get("inode_thresholds", {}) or {}
            fstab_mounts = row.get("fstab_mounts", {}) or {}
            failed_services = row.get("failed_services", []) or []
            print()
            print(f"{palette.bold}{server}{palette.reset} [{palette.status(status)}]")
            print(f"  OS: RHEL {os_data.get('version', '-')}")
            print(f"  Running kernel: {kernel.get('running', '-')}")
            print(f"  Newest installed kernel: {kernel.get('newest_installed') or '-'}")
            print(f"  Next kernel: {kernel.get('planned') or '-'}")
            print(
                f"  Uptime: {row.get('uptime_days', '-')} days "
                f"[{row.get('uptime_severity', '-')}]"
            )
            print(
                "  Updates: "
                f"{updates.get('total', '-')} total, "
                f"{updates.get('kernel', '-')} kernel, "
                f"{updates.get('systemd', '-')} systemd, "
                f"{updates.get('glibc', '-')} glibc"
            )
            for label in ("root", "boot"):
                disk = disk_space.get(label, {}) or {}
                if not disk:
                    continue
                print(
                    f"  Disk {disk.get('path', label)}: "
                    f"{disk.get('free_mb', '-')} MiB free / {disk.get('total_mb', '-')} MiB total; "
                    f"minimum {disk.get('minimum_free_mb', '-')} MiB "
                    f"[{palette.status(str(disk.get('status', 'FAIL')))}]"
                )
            for mount_path in ("/", "/boot"):
                filesystem = next(
                    (item for item in filesystems if item.get("mount") == mount_path), None
                )
                if not filesystem or not filesystem.get("inode_total"):
                    continue
                inode_percent = (
                    int(filesystem.get("inode_used", 0)) * 100 /
                    int(filesystem["inode_total"])
                )
                inode_status = (
                    "FAIL" if inode_percent >= int(inode_thresholds.get("failure_percent", 95))
                    else "WARNING" if inode_percent >= int(inode_thresholds.get("warning_percent", 80))
                    else "PASS"
                )
                print(
                    f"  Inodes {mount_path}: {inode_percent:.1f}% used "
                    f"[{palette.status(inode_status)}]"
                )
            if fstab_mounts:
                print(
                    "  Mandatory fstab mounts: "
                    f"{', '.join(fstab_mounts.get('required', [])) or 'none'}; "
                    f"missing {', '.join(fstab_mounts.get('missing', [])) or 'none'}; "
                    f"read-only {', '.join(fstab_mounts.get('read_only', [])) or 'none'}"
                )
            if failed_services:
                print(
                    "  Failed services: "
                    + ", ".join(service_name(line) for line in failed_services)
                    + f" [{palette.status('WARNING')}]"
                )
            else:
                print(f"  Failed services: none [{palette.status('PASS')}]")
            print(f"  Report: {row.get('report_dir', '-')}")

    satellite_rows = [
        row for row in rows if row.get("registration_mode") == "satellite"
    ]
    if satellite_rows:
        print()
        print(f"{palette.bold}SATELLITE DETAILS{palette.reset}")
        for row in satellite_rows:
            server = row.get("fqdn") or row.get("host")
            satellite = row.get("satellite", {}) or {}
            registration_status = str(satellite.get("registration_status", "unknown"))
            registration_result = "PASS" if registration_status == "Registered" else "FAIL"
            repositories = satellite.get("enabled_repositories", []) or []
            repositories_enabled = bool(satellite.get("all_repositories_enabled", False))
            consumer_matches = bool(satellite.get("consumer_name_matches", False))
            consumer_result = "PASS" if consumer_matches else "FAIL"
            validation_mode = satellite.get("consumer_validation_mode", "unknown")
            print()
            print(f"{palette.bold}{server}{palette.reset}")
            print(f"  Satellite server: {satellite.get('server') or '-'}")
            print(
                f"  Consumer name found: {satellite.get('consumer_name') or '-'} "
                f"[{palette.status(consumer_result)}]"
            )
            print(f"  Expected consumer name: {satellite.get('expected_consumer_name') or '-'}")
            print(f"  Consumer validation: {validation_mode}")
            print(f"  Organization: {satellite.get('organization') or '-'}")
            print(f"  Environment name: {satellite.get('environment_name') or '-'}")
            print(f"  Lifecycle environment: {satellite.get('lifecycle_environment') or '-'}")
            print(f"  Content view: {satellite.get('content_view') or '-'}")
            print(
                f"  Registration status: {registration_status} "
                f"[{palette.status(registration_result)}]"
            )
            print("  Enabled repositories:")
            if repositories:
                repository_result = "PASS" if repositories_enabled else "FAIL"
                for repository in repositories:
                    print(
                        f"    [{palette.status(repository_result)}] "
                        f"{repository} (Enabled=1)"
                    )
            else:
                print(f"    [{palette.status('FAIL')}] none")

    print()
    passed = len(rows) - failed - warned
    print(
        f"Fleet result: {palette.green}{passed} PASS{palette.reset}, "
        f"{palette.yellow}{warned} WARNING{palette.reset}, "
        f"{palette.red}{failed} FAIL{palette.reset}"
    )
    print(f"Reports: {report_root}/*/{args.run_id}/")
    if not rows:
        print(f"{palette.red}[FAIL] No host reports were produced.{palette.reset}")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
