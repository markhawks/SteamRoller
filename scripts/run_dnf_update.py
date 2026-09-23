#!/usr/bin/python3
"""Run one interactive, audited DNF update through SteamRoller."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time


ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
UPDATE_LINE = re.compile(
    r"^[A-Za-z0-9_.+:-]+[.](?:x86_64|noarch|aarch64|ppc64le|s390x|i686)\s+"
)


class UpdateError(Exception):
    """Operator-facing update error."""


def command_result(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=check, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or getattr(error, "stdout", "") or str(error)
        raise UpdateError(detail.strip()) from error


def inventory_hostvars(inventory: str, host: str) -> dict[str, object]:
    result = command_result(["ansible-inventory", "-i", inventory, "--list"])
    try:
        variables = json.loads(result.stdout).get("_meta", {}).get("hostvars", {})
    except json.JSONDecodeError as error:
        raise UpdateError(f"invalid Ansible inventory output: {error}") from error
    if host not in variables:
        raise UpdateError(f"host is not present in inventory: {host}")
    return variables[host]


def ssh_base(host: str, variables: dict[str, object], key: str | None) -> list[str]:
    address = str(variables.get("ansible_host", host))
    user = str(variables.get("ansible_user", "root"))
    port = str(variables.get("ansible_port", 22))
    command = [
        "ssh", "-tt", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        "-p", port,
    ]
    if key:
        command.extend(["-i", key])
    command.append(f"{user}@{address}")
    return command


def privileged(remote_command: str, variables: dict[str, object]) -> str:
    return remote_command if str(variables.get("ansible_user", "root")) == "root" else f"sudo -n {remote_command}"


def stream_transaction(command: list[str], log_path: Path) -> tuple[int, str]:
    collected: list[str] = []
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(1)
            if chunk == "" and process.poll() is not None:
                break
            if not chunk:
                continue
            sys.stdout.write(chunk)
            sys.stdout.flush()
            log.write(chunk)
            collected.append(chunk)
        return_code = process.wait()
    clean_output = ANSI_ESCAPE.sub("", "".join(collected)).replace("\r", "\n")
    log_path.write_text(clean_output, encoding="utf-8")
    return return_code, clean_output


def remote_capture(
    base: list[str], variables: dict[str, object], remote_command: str
) -> subprocess.CompletedProcess[str]:
    return command_result(
        base + [privileged(remote_command, variables)],
        check=False,
    )


def load_precheck(report_root: Path, run_id: str, host: str) -> tuple[dict, Path]:
    candidates = list(report_root.glob(f"*/{run_id}/summary.json"))
    for path in candidates:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("host") == host:
            return data, path.parent
    raise UpdateError("precheck did not produce a summary for the selected host")


def run_precheck(args: argparse.Namespace, run_id: str) -> tuple[dict, Path]:
    command = [
        "ansible-playbook", "-i", args.inventory, args.precheck_playbook,
        "-e", f"@{args.settings}",
    ]
    if args.environment_settings:
        command.extend(["-e", f"@{args.environment_settings}"])
    command.extend(
        [
            "-e", f"steamroller_report_root={args.report_root}",
            "-e", f"steamroller_run_id={run_id}",
            "--limit", args.host,
        ]
    )
    if args.ssh_key:
        command.extend(["--private-key", args.ssh_key])
    print("STEAMROLLER UPDATE PREFLIGHT")
    print(f"Host: {args.host}")
    result = subprocess.run(command, check=False)
    precheck, report_dir = load_precheck(Path(args.report_root), run_id, args.host)
    if result.returncode != 0 or precheck.get("status") == "FAIL":
        raise UpdateError(f"precheck failed; inspect {report_dir / 'precheck.txt'}")
    return precheck, report_dir


def service_name(line: object) -> str:
    fields = str(line).strip().lstrip("●").strip().split()
    return fields[0] if fields else "unknown-service"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--environment-settings")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--ssh-key")
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--precheck-playbook", required=True)
    parser.add_argument("--renderer", required=True)
    args = parser.parse_args()

    started = int(time.time())
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        variables = inventory_hostvars(args.inventory, args.host)
        precheck, report_dir = run_precheck(args, run_id)
        fqdn = str(precheck.get("fqdn") or args.host)
        updates_before = int((precheck.get("updates", {}) or {}).get("total", 0))
        old_kernel = str((precheck.get("kernel", {}) or {}).get("running", ""))
        planned_kernel = str((precheck.get("kernel", {}) or {}).get("planned", ""))
        failed_before = list(precheck.get("failed_services", []) or [])

        print()
        print("DNF UPDATE PLAN")
        print(f"Host: {fqdn}")
        print(f"Packages available: {updates_before}")
        print(f"Current kernel: {old_kernel or '-'}")
        print(f"Expected kernel: {planned_kernel or '-'}")
        print(f"Precheck result: {precheck.get('status', 'UNKNOWN')}")
        print()
        print("DNF will display the complete transaction and ask Is this ok [y/N].")
        print("No package is changed unless you answer y at the native DNF prompt.")
        print()

        base = ssh_base(args.host, variables, args.ssh_key)
        transaction_log = report_dir / "dnf-transaction.log"
        update_command = base + [privileged("dnf upgrade", variables)]
        transaction_rc, transaction_output = stream_transaction(update_command, transaction_log)

        cancelled = (
            transaction_rc != 0
            and "Is this ok" in transaction_output
            and "Complete!" not in transaction_output
        )
        kernel = remote_capture(base, variables, "uname -r")
        installed_kernels = remote_capture(base, variables, "rpm -q --last kernel-core")
        dnf_check = remote_capture(base, variables, "dnf -q check")
        remaining = remote_capture(base, variables, "dnf -q check-update")
        reboot_required = remote_capture(base, variables, "dnf needs-restarting -r")
        failed_after_result = remote_capture(
            base, variables, "systemctl --failed --no-legend --no-pager"
        )
        history = remote_capture(base, variables, "dnf history info last")

        remaining_lines = [
            line for line in remaining.stdout.splitlines() if UPDATE_LINE.match(line)
        ]
        failed_after = [line for line in failed_after_result.stdout.splitlines() if line.strip()]
        before_names = {service_name(line) for line in failed_before}
        new_failed = [line for line in failed_after if service_name(line) not in before_names]
        failures: list[str] = []
        warnings: list[str] = []
        if cancelled:
            warnings.append("DNF transaction was cancelled by the operator")
        elif transaction_rc != 0:
            failures.append(f"DNF transaction exited with code {transaction_rc}")
        if dnf_check.returncode != 0:
            failures.append("dnf check failed after the transaction")
        if kernel.returncode != 0 or installed_kernels.returncode != 0:
            failures.append("Unable to collect post-update kernel state")
        if new_failed:
            failures.append("New failed systemd units appeared after the update")
        if remaining_lines:
            warnings.append(f"{len(remaining_lines)} package updates remain available")
        if reboot_required.returncode == 1:
            warnings.append("A reboot is required to complete the update")

        status = "FAIL" if failures else ("WARNING" if warnings else "PASS")
        newest_kernel = ""
        if installed_kernels.stdout.splitlines():
            newest_kernel = installed_kernels.stdout.splitlines()[0].split()[0]

        summary = {
            "run_id": run_id,
            "host": args.host,
            "fqdn": fqdn,
            "environment": args.environment,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "operation": "dnf_update",
            "duration_seconds": int(time.time()) - started,
            "os": precheck.get("os", {}),
            "kernel": {
                "running": kernel.stdout.strip(),
                "previous": old_kernel,
                "newest_installed": newest_kernel,
                "planned": planned_kernel,
            },
            "updates": {
                "before": updates_before,
                "remaining": len(remaining_lines),
                "total": len(remaining_lines),
            },
            "dnf_update": {
                "transaction_exit_code": transaction_rc,
                "cancelled": cancelled,
                "dnf_check_exit_code": dnf_check.returncode,
                "reboot_required": reboot_required.returncode == 1,
                "remaining_updates": remaining_lines,
                "failed_units_before": failed_before,
                "failed_units_after": failed_after,
                "new_failed_units": new_failed,
                "history": history.stdout,
                "transaction_log": str(transaction_log),
            },
            "warnings": warnings,
            "failures": failures,
        }
        summary_path = report_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        postcheck_path = report_dir / "update-postcheck.txt"
        postcheck_path.write_text(
            "STEAMROLLER DNF UPDATE POSTCHECK\n"
            f"Host: {fqdn}\n"
            f"Result: {status}\n"
            f"Transaction exit code: {transaction_rc}\n"
            f"Previous kernel: {old_kernel}\n"
            f"Current kernel: {kernel.stdout.strip()}\n"
            f"Newest installed kernel: {newest_kernel}\n"
            f"Remaining updates: {len(remaining_lines)}\n"
            f"Reboot required: {'yes' if reboot_required.returncode == 1 else 'no'}\n"
            f"New failed units: {', '.join(service_name(line) for line in new_failed) or 'none'}\n\n"
            "DNF HISTORY LAST\n"
            f"{history.stdout}\n{history.stderr}",
            encoding="utf-8",
        )
        summary_path.chmod(0o640)
        postcheck_path.chmod(0o640)
        transaction_log.chmod(0o640)
        subprocess.run(
            [
                sys.executable, args.renderer,
                "--report-root", args.report_root,
                "--run-id", run_id,
                "--inventory", args.inventory,
                "--environment", args.environment,
                "--expected-host", args.host,
            ],
            check=False,
        )
        return 1 if failures or cancelled else 0
    except (UpdateError, OSError, json.JSONDecodeError) as error:
        print(f"UPDATE FAIL: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
