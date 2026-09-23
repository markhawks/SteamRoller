#!/usr/bin/python3
"""Run one interactive, audited DNF update through SteamRoller."""

import argparse
import base64
import binascii
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import re
import shlex
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


POSTGRESQL_UNIT = "/usr/lib/systemd/system/postgresql.service"


def ssh_base(
    host: str, variables: dict[str, object], key: str | None, *, tty: bool = False
) -> list[str]:
    address = str(variables.get("ansible_host", host))
    user = str(variables.get("ansible_user", "root"))
    port = str(variables.get("ansible_port", 22))
    command = [
        "ssh", "-tt" if tty else "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        "-p", port,
    ]
    if key:
        command.extend(["-i", key])
    command.append(f"{user}@{address}")
    return command


def privileged(remote_command: str, variables: dict[str, object]) -> str:
    return remote_command if str(variables.get("ansible_user", "root")) == "root" else f"sudo -n {remote_command}"


def stream_transaction(command: list[str], log_path: Path) -> tuple[int, str]:
    collected: list[bytes] = []
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(1)
            if chunk == b"" and process.poll() is not None:
                break
            if not chunk:
                continue
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            log.write(chunk)
            collected.append(chunk)
        return_code = process.wait()
    raw_output = b"".join(collected).decode("utf-8", errors="replace")
    clean_output = ANSI_ESCAPE.sub("", raw_output)
    clean_output = clean_output.replace("\r\n", "\n").replace("\r", "\n")
    log_path.write_text(clean_output, encoding="utf-8")
    return return_code, clean_output


def remote_capture(
    base: list[str], variables: dict[str, object], remote_command: str
) -> subprocess.CompletedProcess[str]:
    return command_result(
        base + [privileged(remote_command, variables)],
        check=False,
    )


def rpm_verify_reports_path(output: str, path: str) -> bool:
    return any(
        line.split() and line.split()[-1] == path
        for line in output.splitlines()
    )


def collect_postgresql_unit(
    base: list[str], variables: dict[str, object]
) -> dict[str, object]:
    exists = remote_capture(base, variables, f"test -f {POSTGRESQL_UNIT}")
    if exists.returncode != 0:
        return {"exists": False}
    content = remote_capture(base, variables, f"base64 -w0 {POSTGRESQL_UNIT}")
    if content.returncode != 0:
        raise UpdateError(f"unable to read {POSTGRESQL_UNIT}")
    try:
        unit_bytes = base64.b64decode(content.stdout.strip(), validate=True)
    except (ValueError, binascii.Error) as error:
        raise UpdateError(f"invalid backup data received for {POSTGRESQL_UNIT}") from error
    owner = remote_capture(base, variables, f"rpm -qf {POSTGRESQL_UNIT}")
    verify = remote_capture(base, variables, f"rpm -Vf {POSTGRESQL_UNIT}")
    systemctl_cat = remote_capture(base, variables, "systemctl cat postgresql.service")
    checksum = remote_capture(base, variables, f"sha256sum {POSTGRESQL_UNIT}")
    stat = remote_capture(base, variables, f"stat -c '%U:%G %a %s' {POSTGRESQL_UNIT}")
    verify_output = (verify.stdout + verify.stderr).strip()
    return {
        "exists": True,
        "content": unit_bytes,
        "owner": owner.stdout.strip(),
        "owner_exit_code": owner.returncode,
        "rpm_verify": verify_output,
        "rpm_verify_exit_code": verify.returncode,
        "customized": (
            owner.returncode != 0
            or rpm_verify_reports_path(verify_output, POSTGRESQL_UNIT)
        ),
        "systemctl_cat": systemctl_cat.stdout,
        "checksum": checksum.stdout.split()[0] if checksum.returncode == 0 else "",
        "stat": stat.stdout.strip(),
    }


def write_unit_evidence(report_dir: Path, label: str, state: dict[str, object]) -> None:
    if not state.get("exists"):
        return
    unit_path = report_dir / f"postgresql-unit-{label}.service"
    unit_path.write_bytes(bytes(state["content"]))
    unit_path.chmod(0o640)
    details_path = report_dir / f"postgresql-unit-{label}.txt"
    details_path.write_text(
        f"File: {POSTGRESQL_UNIT}\n"
        f"RPM owner: {state.get('owner') or '-'}\n"
        f"RPM verify exit code: {state.get('rpm_verify_exit_code')}\n"
        f"RPM verify output: {state.get('rpm_verify') or 'none'}\n"
        f"Customized: {'yes' if state.get('customized') else 'no'}\n"
        f"SHA256: {state.get('checksum') or '-'}\n"
        f"Owner/mode/size: {state.get('stat') or '-'}\n\n"
        "SYSTEMCTL CAT\n"
        f"{state.get('systemctl_cat') or ''}",
        encoding="utf-8",
    )
    details_path.chmod(0o640)


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
    parser.add_argument("--ssh-key-selector")
    parser.add_argument("--report-root", required=True)
    parser.add_argument("--precheck-playbook", required=True)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--postgresql-unit-mode", choices=("backup", "restore"))
    args = parser.parse_args()

    started = int(time.time())
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        variables = inventory_hostvars(args.inventory, args.host)
        precheck, report_dir = run_precheck(args, run_id)
        fqdn = str(precheck.get("fqdn") or args.host)
        reboot_command_parts = [
            "steamroller", "reboot", args.environment, "--host", args.host,
        ]
        if args.ssh_key_selector:
            reboot_command_parts.extend(["-sk", args.ssh_key_selector])
        reboot_command = shlex.join(reboot_command_parts)
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
        postgresql_before: dict[str, object] = {"exists": False}
        postgresql_remote_backup = ""
        if args.postgresql_unit_mode:
            postgresql_before = collect_postgresql_unit(base, variables)
            if postgresql_before.get("exists"):
                write_unit_evidence(report_dir, "before", postgresql_before)
                postgresql_remote_backup = (
                    f"/var/lib/steamroller/backups/postgresql-unit/{run_id}"
                    "/postgresql.service"
                )
                backup_command = (
                    f"install -d -m 0700 /var/lib/steamroller/backups/postgresql-unit/{run_id}"
                    f" && cp -a {POSTGRESQL_UNIT} {postgresql_remote_backup}"
                    f" && chmod 0600 {postgresql_remote_backup}"
                )
                backup_result = remote_capture(base, variables, backup_command)
                if backup_result.returncode != 0:
                    raise UpdateError("unable to create the remote PostgreSQL unit backup")
                print("PostgreSQL unit protection:")
                print(f"  Mode: {args.postgresql_unit_mode}")
                print(f"  Customized: {'yes' if postgresql_before.get('customized') else 'no'}")
                print(f"  Remote backup: {postgresql_remote_backup}")
                print(f"  Local evidence: {report_dir}")
                print()
            else:
                print(f"PostgreSQL unit protection: {POSTGRESQL_UNIT} not found; skipped")
                print()
        transaction_log = report_dir / "dnf-transaction.log"
        update_command = ssh_base(args.host, variables, args.ssh_key, tty=True) + [
            privileged("dnf upgrade", variables)
        ]
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

        postgresql_after: dict[str, object] = {"exists": False}
        postgresql_restored = False
        postgresql_restore_valid = False
        postgresql_restore_validation = "not requested"
        postgresql_diff_path = ""
        if args.postgresql_unit_mode and postgresql_before.get("exists"):
            postgresql_after = collect_postgresql_unit(base, variables)
            write_unit_evidence(report_dir, "after-update", postgresql_after)
            before_text = bytes(postgresql_before["content"]).decode(
                "utf-8", errors="replace"
            ).splitlines(keepends=True)
            after_text = bytes(postgresql_after.get("content", b"")).decode(
                "utf-8", errors="replace"
            ).splitlines(keepends=True)
            diff_text = "".join(
                difflib.unified_diff(
                    before_text,
                    after_text,
                    fromfile="postgresql.service.before",
                    tofile="postgresql.service.after-update",
                )
            )
            diff_file = report_dir / "postgresql-unit.diff"
            diff_file.write_text(diff_text or "No differences.\n", encoding="utf-8")
            diff_file.chmod(0o640)
            postgresql_diff_path = str(diff_file)

            if (
                args.postgresql_unit_mode == "restore"
                and postgresql_before.get("customized")
                and not cancelled
            ):
                restore_command = (
                    f"cp -a {postgresql_remote_backup} {POSTGRESQL_UNIT}"
                    " && systemctl daemon-reload"
                )
                restore_result = remote_capture(base, variables, restore_command)
                if restore_result.returncode == 0:
                    restored_state = collect_postgresql_unit(base, variables)
                    postgresql_restored = (
                        restored_state.get("checksum")
                        == postgresql_before.get("checksum")
                    )
                    write_unit_evidence(
                        report_dir,
                        "restored",
                        restored_state,
                    )
                    verify_result = remote_capture(
                        base, variables, f"systemd-analyze verify {POSTGRESQL_UNIT}"
                    )
                    postgresql_restore_valid = (
                        postgresql_restored and verify_result.returncode == 0
                    )
                    postgresql_restore_validation = (
                        "PASS" if postgresql_restore_valid else
                        (verify_result.stdout + verify_result.stderr).strip()
                        or "restored checksum does not match the backup"
                    )
                else:
                    postgresql_restore_validation = (
                        (restore_result.stdout + restore_result.stderr).strip()
                        or "restore command failed"
                    )
            elif args.postgresql_unit_mode == "restore":
                postgresql_restore_validation = (
                    "not performed; DNF transaction was cancelled"
                    if cancelled else "not needed; unit was not customized"
                )

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
        if args.postgresql_unit_mode == "backup" and postgresql_before.get("customized"):
            if postgresql_before.get("checksum") != postgresql_after.get("checksum"):
                warnings.append(
                    "Customized PostgreSQL unit changed during update; review the saved diff"
                )
        if (
            args.postgresql_unit_mode == "restore"
            and postgresql_before.get("customized")
            and not cancelled
            and not postgresql_restore_valid
        ):
            failures.append("Customized PostgreSQL unit could not be restored and validated")

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
                "suggested_reboot_command": reboot_command,
                "postgresql_unit": {
                    "mode": args.postgresql_unit_mode or "disabled",
                    "path": POSTGRESQL_UNIT,
                    "present_before": bool(postgresql_before.get("exists")),
                    "customized_before": bool(postgresql_before.get("customized")),
                    "rpm_owner": postgresql_before.get("owner", ""),
                    "checksum_before": postgresql_before.get("checksum", ""),
                    "checksum_after_update": postgresql_after.get("checksum", ""),
                    "remote_backup": postgresql_remote_backup,
                    "diff": postgresql_diff_path,
                    "restored": postgresql_restored,
                    "restore_valid": postgresql_restore_valid,
                    "restore_validation": postgresql_restore_validation,
                },
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
            f"New failed units: {', '.join(service_name(line) for line in new_failed) or 'none'}\n"
            f"PostgreSQL unit mode: {args.postgresql_unit_mode or 'disabled'}\n"
            f"PostgreSQL unit customized before: "
            f"{'yes' if postgresql_before.get('customized') else 'no'}\n"
            f"PostgreSQL unit restored: {'yes' if postgresql_restored else 'no'}\n"
            f"PostgreSQL restore validation: {postgresql_restore_validation}\n\n"
            f"Suggested reboot command: {reboot_command}\n\n"
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
