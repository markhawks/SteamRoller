#!/usr/bin/python3
"""List SteamRoller report runs in an operator-friendly table."""

import argparse
from datetime import datetime, timezone
from pathlib import Path


def run_time(run_id: str) -> str:
    try:
        utc_time = datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
        return utc_time.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        return "unknown"


def run_type(directory: Path) -> str:
    if (directory / "update-postcheck.txt").is_file():
        return "DNF-UPDATE"
    if (directory / "reboot.txt").is_file():
        return "REBOOT"
    if (directory / "reboot-pre.txt").is_file():
        return "REBOOT-STARTED"
    if (directory / "precheck.txt").is_file():
        return "PRECHECK"
    if (directory / "connectivity.txt").is_file():
        return "CONNECTIVITY"
    if (directory / "repo-quarantine.txt").is_file():
        return "REPO-OFF"
    return "INCOMPLETE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args()
    report_root = Path(args.report_root)

    if not report_root.is_dir():
        print(f"No reports found in {report_root}")
        return 0

    rows: list[tuple[str, str, str, str]] = []
    for server_directory in report_root.iterdir():
        if not server_directory.is_dir():
            continue
        for run_directory in server_directory.iterdir():
            if not run_directory.is_dir():
                continue
            run_id = run_directory.name
            rows.append(
                (
                    server_directory.name,
                    run_time(run_id),
                    run_id,
                    run_type(run_directory),
                )
            )

    if not rows:
        print(f"No reports found in {report_root}")
        return 0

    rows.sort(key=lambda row: row[2], reverse=True)
    widths = (
        max(24, max(len(row[0]) for row in rows)),
        max(24, max(len(row[1]) for row in rows)),
        max(16, max(len(row[2]) for row in rows)),
        max(12, max(len(row[3]) for row in rows)),
    )
    headers = ("SERVER", "EXECUTION TIME", "RUN ID", "TYPE")
    print("  ".join(f"{header:<{width}}" for header, width in zip(headers, widths)))
    print("  ".join("-" * width for width in widths))
    for server, execution_time, run_id, kind in rows:
        values = (server, execution_time, run_id, kind)
        print("  ".join(f"{value:<{width}}" for value, width in zip(values, widths)))

    connectivity_servers = sorted({row[0] for row in rows if row[3] == "CONNECTIVITY"})
    precheck_servers = sorted({row[0] for row in rows if row[3] == "PRECHECK"})
    reboot_servers = sorted({row[0] for row in rows if row[3] == "REBOOT"})
    update_servers = sorted({row[0] for row in rows if row[3] == "DNF-UPDATE"})
    if connectivity_servers:
        print()
        print("CONNECTIVITY directories: " + ", ".join(connectivity_servers))
    if precheck_servers:
        print("PRECHECK report directories: " + ", ".join(precheck_servers))
    if reboot_servers:
        print("REBOOT report directories: " + ", ".join(reboot_servers))
    if update_servers:
        print("DNF-UPDATE report directories: " + ", ".join(update_servers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
