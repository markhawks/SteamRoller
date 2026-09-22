# SteamRoller Project Status

Last updated: 2026-09-17
Current version: 0.1.0
Status: active development

License: GNU Affero General Public License v3.0 or later

## Current scope

SteamRoller v1 is a read-only validation and evidence-collection tool for
remote Red Hat Enterprise Linux 9.x systems. The Ansible control node may run
RHEL 9 or RHEL 10.

Package installation, system patching, reboot orchestration, post-patch
validation, and PRE/POST comparison are not part of the first release.

The project currently supports hosts registered directly with Red Hat CDN.
Satellite-specific validation is planned for a later environment and must not
modify Content Views, Lifecycle Environments, or repository assignments.

Cluster and HA detection is temporarily disabled for the initial single-host
laboratory.

## Implemented operator commands

```bash
./bin/steamroller doctor dev
./bin/steamroller config dev
./bin/steamroller connectivity dev
./bin/steamroller connectivity dev --quiet
./bin/steamroller precheck dev
./bin/steamroller precheck dev --quiet
./bin/steamroller status
```

A dedicated private key can be selected at runtime with `--ssh-key PATH` or
the `STEAMROLLER_SSH_KEY` environment variable. The key is validated locally
and is never copied into reports or the repository.

Normal mode displays Ansible task progress and the final fleet report. Quiet
mode suppresses task progress but always displays the final report and any
blocking findings.

The reporting interface is designed for inventories containing approximately
5 to 10 hosts. Every inventory host receives a row, including unreachable
hosts and hosts that failed before producing a report.

## Implemented validation

### Connectivity and identity

- SSH and Ansible Python connectivity;
- configured remote user;
- root command execution;
- hostname, FQDN, environment, and run ID;
- RHEL distribution and release identification;
- RHEL 9.x-only managed-host policy.

### Kernel and uptime

- running kernel;
- installed kernel packages;
- newest installed kernel based on RPM installation time;
- warning when the running kernel differs from the newest installed kernel;
- next kernel expected from the available `kernel-core` update;
- uptime severity:
  - 0-89 days: `PASS`;
  - 90-179 days: `WARNING`;
  - 180-364 days: `HIGH WARNING`;
  - 365 days or more: `CRITICAL WARNING`.

### Red Hat registration and repositories

- `subscription-manager identity` and status;
- enabled repository collection;
- required repository ID validation;
- DNF repository provenance without storing repository secrets;
- discovery of `/etc/yum.repos.d/*.repo` files;
- `redhat.repo` allowed by default;
- additional `.repo` files fail precheck by default;
- explicit repository quarantine utility with a protected local backup.

Repository quarantine is a separate, explicitly requested administrative
operation. It is never executed automatically by read-only precheck:

```bash
./bin/steamroller repo-off dev
```

### DNF and RPM health

- detection of concurrent `dnf`, `yum`, and `rpm` processes;
- read-only `dnf check` dependency validation;
- `dnf check-update`, with return code 100 correctly treated as success;
- total available update count;
- separate kernel, systemd, and glibc update counts;
- pre-existing reboot requirement detection.

### Filesystems, disk space, and inodes

Absolute free space is the blocking criterion:

```yaml
steamroller_root_min_free_mb: 4096
steamroller_boot_min_free_mb: 400
```

Percentage use remains an additional warning indicator and is not, by itself,
a blocking capacity decision.

Inode limits are:

```yaml
steamroller_inode_warning_percent: 80
steamroller_inode_failure_percent: 95
```

Mandatory mount points are derived from `/etc/fstab`. Swap and entries using
`noauto` are excluded. A mandatory mount that is missing or read-only fails
precheck.

### Network and services

- IP address collection;
- routing-table collection;
- NetworkManager device status when available;
- running, enabled, and failed service evidence;
- services failed at precheck time reported by name as warnings.

Application-specific and critical-service policies are not yet enabled.

## Configuration

Global defaults are stored in:

```text
config/steamroller.yml
```

The future RPM location is:

```text
/etc/steamroller/steamroller.yml
```

Effective non-sensitive configuration can be displayed with:

```bash
./bin/steamroller config dev
```

Configuration is validated locally before contacting managed hosts. Invalid
percentages, thresholds, policy names, value types, or an empty inventory stop
execution with `CONFIG FAIL`.

## Reports

Reports use the remote server name and immutable run ID:

```text
reports/SERVER_NAME/RUN_ID/
```

A typical precheck produces:

```text
checks.json
filesystem.txt
kernel.txt
mounts.txt
network.txt
os.txt
precheck.txt
repo-files.txt
repositories.txt
services-enabled.txt
services-failed.txt
services-running.txt
subscription.txt
summary.json
updates-planned.txt
uptime.txt
```

The final terminal report includes fleet counts, per-host status, current and
next kernel, update counts, absolute disk capacity, inode use, mandatory mount
state, warning and failure details, and the exact report directory.

## Result model

Each read-only precheck host currently ends with:

```text
PASS
WARNING
FAIL
```

Unreachable hosts and hosts that do not produce evidence are displayed as
failures in the fleet summary. Any blocking host causes a non-zero command exit
status.

## Security and repository hygiene

- SSH host-key checking remains enabled;
- passwords, tokens, private keys, and sudo credentials must not be committed;
- real customer inventories are ignored by Git;
- runtime reports and repository backups are ignored by Git;
- repository backup files use mode `0600`;
- normal report directories use mode `0750`;
- precheck never modifies the managed host.

## License and public development

SteamRoller is publicly developed under the GNU Affero General Public License,
version 3 or any later version (`AGPL-3.0-or-later`). Network users must be
offered the corresponding source code as required by the license. The complete
license text is provided in `LICENSE`.

## Source and future installation layout

Development runs directly from the cloned source tree. RPM creation is being
deferred until the read-only release is complete and validated on real systems.

The planned installed layout is:

```text
/opt/steamroller/                 application code
/etc/steamroller/                 configuration and inventories
/var/lib/steamroller/reports/     persistent evidence
/var/log/steamroller/             operational logs
/usr/bin/steamroller              operator entry point
```

## Remaining work for read-only v1

- test negative paths for unsupported OS, invalid registration, unavailable
  repositories, DNF concurrency, inode exhaustion, missing fstab mounts, and
  unreachable hosts;
- test the fleet summary with multiple real hosts;
- decide and implement the final fleet-level persistent summary format;
- complete normalized structured evidence only where required by operations;
- document customer onboarding and inventory creation;
- document report retention and backup policy;
- validate source-based operation from clean RHEL 9 and RHEL 10 control nodes;
- defer RPM build and installation tests until the read-only behavior is
  accepted.

## Explicitly deferred

- package updates;
- automatic reboot;
- post-patch checks;
- PRE/POST comparison;
- automatic filesystem cleanup;
- automatic RPM database repair;
- automatic repository modification during precheck;
- cluster and HA automation;
- application changes;
- custom GUI.
