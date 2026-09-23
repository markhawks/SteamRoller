# SteamRoller Project Status

Last updated: 2026-09-23

Current version: **0.2.0**

Status: version 0.2.0 validated on real RHEL 9 systems; post-release update
workflow under active development

License: AGPL-3.0-or-later

## Current development scope

SteamRoller manages remote RHEL 9.x hosts from a RHEL 9 or RHEL 10
control node. Its primary workflow is read-only assessment and evidence
collection. Three changes to managed hosts require explicit operator action:

- quarantine of custom repository files;
- reboot of one exact inventory host;
- interactive DNF update of one exact inventory host.

Unattended fleet updates, automatic fleet reboot, and cluster/HA orchestration
are not implemented.

## Implemented commands

```text
steamroller version
steamroller doctor ENVIRONMENT
steamroller config [ENVIRONMENT]
steamroller inventory create|add|del|list
steamroller connectivity ENVIRONMENT
steamroller precheck ENVIRONMENT
steamroller repo-off ENVIRONMENT
steamroller reboot ENVIRONMENT --host HOST
steamroller update ENVIRONMENT --host HOST
steamroller status
```

All operational commands support persistent reporting. Connectivity, precheck,
repository quarantine, reboot, and update accept SSH key profiles. Update is
always interactive and intentionally does not accept `-q`/`--quiet`.

## Implemented validation

### Inventory and access

- atomic inventory creation and modification;
- hostname ping and IPv4 discovery before inventory writes;
- default SSH user `root` and port `22`, with overrides;
- context-sensitive Bash completion;
- named SSH key profiles and automatic private-key discovery;
- SSH, Python, and root-execution checks.

### Platform and lifecycle

- RHEL 9.x managed-host policy;
- running, installed, newest installed, and planned kernels;
- uptime severity at 90, 180, and 365 days;
- update totals for kernel, systemd, and glibc;
- pre-existing reboot requirement.

### Subscription and Satellite

- RHSM identity and registration validation;
- automatic CDN versus Satellite detection;
- Simple Content Access-aware status handling;
- consumer/FQDN comparison;
- Organization, Satellite server, Lifecycle Environment, and Content View;
- enabled repository IDs and `Enabled=1` validation;
- optional expected Satellite values per environment.

### Repository safety

- scan of `/etc/yum.repos.d/*.repo`;
- `redhat.repo` allowed by default;
- additional files fail precheck by default;
- explicit local backup and remote quarantine;
- optional `precheck --repo-off` workflow;
- per-host action summary and manifest.

### PostgreSQL

- all installed `postgresql*` RPMs and versions;
- RPM vendor and packager evidence;
- `RED HAT`, `COMMUNITY (PGDG)`, `MIXED`, `UNKNOWN`, or `NOT INSTALLED`;
- warnings for mixed or unknown provenance;
- available PostgreSQL versions and source repositories;
- dedicated terminal, text, and JSON evidence.
- optional protection for a customized
  `/usr/lib/systemd/system/postgresql.service` during DNF update;
- `backup` mode preserves the unit and reports the vendor-file differences;
- `restore` mode restores only a unit identified as customized, runs
  `daemon-reload`, verifies its checksum, and validates it with
  `systemd-analyze verify`;
- PostgreSQL is never restarted automatically.

### Capacity, mounts, and system state

- at least 4096 MiB free on `/`;
- at least 400 MiB free on `/boot`;
- inode warnings at 80% and failures at 95%;
- mandatory mounts derived from `/etc/fstab`;
- missing and read-only mandatory mounts;
- IP addresses, routing, and NetworkManager state;
- running, enabled, and failed systemd units;
- `dnf check` and package-manager concurrency.

### Controlled reboot

- exactly one host selected from the requested inventory;
- typed interactive confirmation or explicit `--confirm`;
- block while `dnf`, `yum`, or `rpm` is active;
- mandatory mount validation before and after reboot;
- PRE evidence written before changing state;
- SSH return and boot-ID change validation;
- old/new kernel and uptime comparison;
- detection of newly failed systemd units;
- configurable timeout, default 900 seconds.

### Interactive DNF update

- exactly one host selected from the requested inventory;
- complete precheck executed immediately before updating;
- blocking precheck failures stop the operation;
- native `dnf upgrade` transaction displayed through an SSH pseudo-terminal;
- package installation requires the native DNF `Is this ok [y/N]` answer;
- reviewed policy failures can be overridden with `-F`/`--force`, typed host
  confirmation, explicit audit evidence, and a minimum `WARNING` result;
- read-only mandatory fstab mounts are overridable, while missing mounts and
  read-only critical filesystems remain hard blockers;
- complete transaction log and DNF history evidence;
- optional PostgreSQL vendor-unit backup, comparison, and explicit restoration;
- remaining updates, kernel state, `dnf check`, reboot requirement, and newly
  failed systemd units checked after the transaction;
- complete suggested SteamRoller reboot command in the final report;
- no automatic reboot.

## Reporting

Each run uses an immutable UTC run ID and per-server directory. The terminal
summary covers every expected host, including unreachable hosts. Reports are
classified as `CONNECTIVITY`, `PRECHECK`, `REPO-OFF`, `REBOOT`, `DNF-UPDATE`,
or incomplete.

A typical precheck report contains:

```text
checks.json
filesystem.txt
kernel.txt
mounts.txt
network.txt
os.txt
postgresql.txt
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

## Configuration defaults

```yaml
steamroller_registration_mode: auto
steamroller_root_min_free_mb: 4096
steamroller_boot_min_free_mb: 400
steamroller_inode_warning_percent: 80
steamroller_inode_failure_percent: 95
steamroller_uptime_warning_days: 90
steamroller_uptime_high_days: 180
steamroller_uptime_critical_days: 365
steamroller_custom_repo_policy: fail
steamroller_allowed_repo_files:
  - redhat.repo
```

Configuration is validated before contacting managed hosts.

## Verification completed

- Bash and Python syntax checks;
- Ansible syntax checks for all playbooks;
- inventory-manager create/add/delete/list and atomic-failure tests;
- SSH-key discovery and Bash completion tests;
- multi-host precheck on real Satellite-managed RHEL 9 systems;
- Satellite Simple Content Access behavior;
- repository quarantine, including the opt-in precheck workflow;
- PostgreSQL package provenance and update reporting;
- managed SSH profiles and quiet-mode execution;
- controlled single-host reboot on a real non-production system;
- successful SSH return, boot-ID change, kernel comparison, mandatory-mount
  checks, and PRE/POST reboot reporting.
- interactive single-host DNF update on a real test system;
- native DNF terminal display and manual confirmation;
- automated tests for PostgreSQL unit detection and update-option completion.

The 0.2.0 workflow and the subsequent interactive DNF update have been
exercised successfully by the operator. PostgreSQL unit restoration still
requires validation on a non-production host containing a customized unit.

## Security model

- SSH host-key verification stays enabled;
- private keys, inventories, reports, and repository backups are ignored by Git;
- private-key contents are never included in reports;
- normal checks remain read-only;
- mutating commands require an explicit action or option;
- repository and PostgreSQL unit backups use mode `0600`;
- report directories use mode `0750`.

## Remaining work

- expand negative-path testing for DNF locks, damaged RPM state, missing mounts,
  inode exhaustion, and hosts that do not return after reboot;
- validate source installation from clean RHEL 9 and RHEL 10 control nodes;
- define report retention and backup policy;
- improve failed-systemd-unit classification by unit type;
- complete RPM build and clean installation testing;
- validate PostgreSQL unit `backup` and `restore` modes on a non-production host;
- implement a dedicated postcheck and PRE/POST maintenance comparison.

## Explicitly deferred

- automatic or multi-host reboot;
- unattended or multi-host package updates;
- cluster and HA detection/orchestration;
- application stop/start workflows;
- automatic filesystem cleanup;
- automatic RPM database repair;
- Satellite Content View or Lifecycle Environment changes;
- graphical interface.
