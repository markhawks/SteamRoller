# SteamRoller 0.3.1 Operator HOWTO

This document describes every SteamRoller command available in version 0.3.1.
Examples assume a source checkout in `/root/SteamRoller` and root execution.

## 1. Install the source command and completion

```bash
cd /root/SteamRoller
./setup/manual/install-source-path.sh
source /root/.bashrc
```

Verify the installation:

```bash
command -v steamroller
steamroller version
```

Expected version:

```text
0.3.1
```

The installer can be run repeatedly. It replaces its managed `.bashrc` block
and creates a timestamped backup. Remove the managed block with:

```bash
./setup/manual/install-source-path.sh --remove
source /root/.bashrc
```

## 2. Bash completion

Press `Tab` twice after commands and options:

```text
steamroller <Tab><Tab>
steamroller precheck <Tab><Tab>
steamroller reboot ENVIRONMENT --host <Tab><Tab>
steamroller precheck ENVIRONMENT -sk <Tab><Tab>
```

Completion suggests commands, environments, inventory hosts, SSH profiles,
and context-specific options.

## 3. SSH key profiles

Create one directory per identity beneath `ssh-keys/`:

```bash
mkdir -p ssh-keys/foreman
cp /secure/path/id_rsa_foreman_proxy ssh-keys/foreman/
chmod 700 ssh-keys ssh-keys/foreman
chmod 600 ssh-keys/foreman/id_rsa_foreman_proxy
```

Exactly one private key must exist inside each profile. Public `.pub` files are
ignored. With one private key across all profiles, selection is automatic.
With multiple profiles, select one using either form:

```bash
-sk foreman
--ssh-key foreman
```

A direct path remains valid:

```bash
--ssh-key /secure/path/id_ed25519
```

Environment variables:

```text
STEAMROLLER_SSH_KEY          default profile or key selector
STEAMROLLER_SSH_KEY_ROOT     alternate managed-key directory
```

## 4. Version

```bash
steamroller version
```

Prints the installed or checked-out SteamRoller version.

## 5. Inventory management

### Create an inventory

```bash
steamroller inventory create \
  -i ORION-LAB \
  -h velora-db-a01.ops.example \
  -h velora-db-a02.ops.example
```

Defaults:

```text
SSH port: 22
SSH user: root
```

Override both for all hosts in the command:

```bash
steamroller inventory create \
  -i NEBULA-LAB \
  -h caelix-app-a01.ops.example \
  -h caelix-app-a02.ops.example \
  -p 2222 \
  -u operator
```

Before writing, SteamRoller pings every hostname and extracts its IPv4 address.
The operation is atomic: one failure prevents the entire write.

### Add hosts

```bash
steamroller inventory add \
  -i ORION-LAB \
  -h velora-db-a03.ops.example \
  -h velora-db-a04.ops.example
```

`-p` and `-u` are supported as with `create`. Existing host aliases are rejected.

### Delete hosts

```bash
steamroller inventory del \
  -i ORION-LAB \
  -h velora-db-a03.ops.example \
  -h velora-db-a04.ops.example
```

Every requested host must already exist; otherwise no host is removed.

### List inventories

```bash
steamroller inventory list
```

### List inventory hosts and IP addresses

```bash
steamroller inventory list ORION-LAB
```

## 6. Doctor

```bash
steamroller doctor ORION-LAB
```

Checks local executables, readable configuration, and inventory syntax without
contacting managed hosts.

## 7. Effective configuration

```bash
steamroller config ORION-LAB
```

With no environment, `dev` is used:

```bash
steamroller config
```

Global settings are loaded from `config/steamroller.yml`. Optional settings in
`inventories/ENVIRONMENT/steamroller.yml` override global values for that
environment. Runtime-protected values such as report root and run ID cannot be
overridden by the environment file.

Default uptime levels are:

```yaml
steamroller_uptime_warning_days: 30
steamroller_uptime_high_days: 90
steamroller_uptime_critical_days: 200
```

The precheck reports `WARNING` from day 30, `HIGH WARNING` from day 90, and
`CRITICAL WARNING` from day 200. Every non-PASS uptime level includes the
complete suggested SteamRoller reboot command.

## 8. Connectivity

```bash
steamroller connectivity ORION-LAB -sk foreman
```

Quiet mode suppresses Ansible task output but always prints the final summary:

```bash
steamroller connectivity ORION-LAB -q -sk foreman
```

The command verifies SSH, Ansible Python, root execution, hostname, and FQDN
for every inventory host. Unreachable hosts remain visible as failures.

## 9. Precheck

```bash
steamroller precheck ORION-LAB -q -sk foreman
```

Precheck is read-only unless `--repo-off` is explicitly supplied. It collects:

- RHEL release and package identity;
- running, installed, newest, and planned kernels;
- uptime severity and reboot requirement;
- RHSM/CDN/Satellite identity and repositories;
- DNF health and available updates;
- PostgreSQL RPMs, vendor, provenance, and available versions;
- disk capacity, inode usage, fstab mounts, and read-only state;
- network and NetworkManager information;
- running, enabled, and failed systemd units;
- custom repository configuration files.

Result levels:

```text
PASS       all blocking checks passed
WARNING    operation may proceed after operator review
FAIL       one or more blocking conditions exist
```

Quiet aliases are equivalent:

```text
-q
--quiet
```

## 10. Precheck with repository quarantine

```bash
steamroller precheck ORION-LAB \
  --repo-off \
  -q \
  -sk foreman
```

This explicitly changes the managed host. For each non-allowed `.repo` file it:

1. creates a protected local backup;
2. creates `/etc/yum.repos.d/SteamRoller-RepoOff/RUN_ID/`;
3. moves the file into that remote directory;
4. runs the complete precheck against the resulting configuration;
5. reports every file moved.

## 11. Standalone repository quarantine

```bash
steamroller repo-off ORION-LAB -q -sk foreman
```

This performs only the explicit backup and quarantine operation. It does not
run the complete precheck afterward.

## 12. Controlled sequential reboot

Interactive execution:

```bash
steamroller reboot ORION-LAB \
  --host velora-db-a01.ops.example \
  --host velora-db-a02.ops.example \
  -sk foreman
```

Each hostname must be an exact alias from the selected inventory. SteamRoller
shows the ordered target list and asks the operator to type:

```text
REBOOT velora-db-a01.ops.example velora-db-a02.ops.example
```

Non-interactive execution requires explicit authorization:

```bash
steamroller reboot ORION-LAB \
  --host velora-db-a01.ops.example \
  -sk foreman \
  --confirm \
  -q
```

Change the default 900-second timeout:

```bash
steamroller reboot ORION-LAB \
  --host velora-db-a01.ops.example \
  --timeout 1200 \
  -sk foreman
```

Safety behavior:

- one or more explicitly selected inventory hosts are accepted;
- every host requires a separate `--host` option;
- hosts are processed sequentially with Ansible `serial: 1`;
- active `dnf`, `yum`, or `rpm` blocks reboot;
- missing mandatory fstab mounts block reboot;
- PRE evidence is written before changing state;
- SSH return and boot-ID change are verified;
- mounts, kernel, uptime, and failed units are checked after reboot;
- newly failed units produce a failed result.

There is no `--all` reboot option in version 0.3.1; SteamRoller never expands
the command to the complete inventory implicitly.

## 13. Interactive single-host DNF update

```bash
steamroller update ORION-LAB \
  --host velora-db-a01.ops.example \
  -sk foreman
```

The environment and host are available through Bash completion. Update accepts
one exact inventory host only and requires a real interactive terminal. It does
not support `-q`, `--quiet`, or an automatic confirmation option.

SteamRoller first executes the complete precheck against the selected host. A
precheck `FAIL` stops the operation; `PASS` and reviewed `WARNING` results may
continue. DNF then displays its normal package transaction and asks:

```text
Is this ok [y/N]:
```

Answer `y` to authorize package changes or press Enter/answer `n` to cancel.
Afterward SteamRoller records the transaction, DNF history, remaining updates,
kernel state, reboot requirement, package consistency, and newly failed
systemd units. It never reboots automatically. The final report prints a
complete interactive `steamroller reboot` command for the updated host,
including the SSH key selector when one was supplied.

### Force reviewed policy failures

Run the normal update first. If its precheck stops on a reviewed false positive,
repeat it with either `-F` or `--force` (`--Force` is also accepted):

```bash
steamroller update ORION-LAB \
  --host velora-db-a01.ops.example \
  -sk foreman \
  -F
```

SteamRoller reruns the complete precheck, separates overridable findings from
hard blockers, and shows everything that would be ignored. If no hard blocker
is present, it requires the exact interactive confirmation:

```text
FORCE UPDATE velora-db-a01.ops.example
```

The native DNF `[y/N]` confirmation is still required afterward. The report is
marked `FORCED`, lists every overridden finding, and has a minimum result of
`WARNING`.

Typical overridable findings include custom repository policy, expected
Satellite-value mismatches, PostgreSQL inventory collection, and a mandatory
fstab mount detected as read-only. A missing mandatory mount is never
overridable. A read-only critical filesystem (`/`, `/boot`, `/boot/efi`, `/var`,
`/var/log`, or `/tmp`) also remains a hard blocker.

Other hard blockers include insufficient free space or inodes, unsupported OS,
failed mandatory collection, unavailable required repositories, `dnf check` or
update-query failure, and an active `dnf`, `yum`, or `rpm` process.

### Protect a customized PostgreSQL systemd unit

Some legacy systems contain local changes directly in:

```text
/usr/lib/systemd/system/postgresql.service
```

Back up the unit and report changes without restoring it:

```bash
steamroller update ORION-LAB \
  --host velora-db-a01.ops.example \
  -sk foreman \
  --preserve-postgresql-unit backup
```

Explicitly restore a unit that RPM verification identified as customized:

```bash
steamroller update ORION-LAB \
  --host velora-db-a01.ops.example \
  -sk foreman \
  --preserve-postgresql-unit restore
```

Both modes create protected local and remote evidence, capture `systemctl cat`,
record the owning RPM, calculate checksums, and produce a unified difference.
`restore` runs `systemctl daemon-reload` and `systemd-analyze verify` after
copying the customized unit back. It does not restart PostgreSQL.

Tab completion is available for the mode:

```bash
steamroller update ORION-LAB --host velora-db-a01.ops.example \
  --preserve-postgresql-unit <TAB><TAB>
```

Expected suggestions:

```text
backup  restore
```

The remote backup is stored with mode `0600` at:

```text
/var/lib/steamroller/backups/postgresql-unit/RUN_ID/postgresql.service
```

The local report can contain:

```text
postgresql-unit-before.service
postgresql-unit-before.txt
postgresql-unit-after-update.service
postgresql-unit-after-update.txt
postgresql-unit-restored.service
postgresql-unit-restored.txt
postgresql-unit.diff
```

The `restored` files are created only when restoration is necessary and
successful. If DNF is cancelled, SteamRoller retains the backup but does not
perform an unnecessary restore. A failed copy, checksum comparison, systemd
reload, or unit validation makes the update result `FAIL`.

Restoring the complete vendor unit is a compatibility measure. The recommended
permanent solution is to migrate local directives to:

```text
/etc/systemd/system/postgresql.service.d/override.conf
```

## 14. Report status

```bash
steamroller status
```

Shows server, local execution time, UTC run ID, and operation type. Types
include `CONNECTIVITY`, `PRECHECK`, `REPO-OFF`, `REBOOT`, `DNF-UPDATE`, and
incomplete runs.

Reports from a source checkout are stored in:

```text
reports/SERVER_NAME/RUN_ID/
```

## 15. Satellite environment expectations

Create an optional environment configuration:

```bash
cp inventories/dev/steamroller.yml.example \
   inventories/ORION-LAB/steamroller.yml
```

Example:

```yaml
---
steamroller_registration_mode: auto
steamroller_expected_satellite_server: astrion-sat-a01.ops.example
steamroller_expected_consumer_name: ""
steamroller_expected_organization: ExampleOrg
steamroller_expected_lifecycle_environment: Testing
steamroller_expected_content_view: Red_Hat_9_8
steamroller_required_repositories:
  - rhel-9-for-x86_64-baseos-rpms
  - rhel-9-for-x86_64-appstream-rpms
```

An empty expected consumer name means that each discovered Satellite consumer
name is compared automatically with that host's FQDN. Both values and the
validation mode remain visible in the report.

## 16. Standalone Satellite diagnostic

Run directly on a managed host:

```bash
sudo ./scripts/test_satellite_check.sh
```

This is a focused diagnostic. The normal remote workflow is `steamroller
precheck`.

## 17. Exit behavior

- `0`: requested operation and fleet result succeeded;
- non-zero: invalid local configuration, unreachable host, failed check,
  cancelled reboot or update, Ansible failure, or failed post-operation
  validation.

Always inspect the final summary and referenced report directory before
continuing with maintenance.
