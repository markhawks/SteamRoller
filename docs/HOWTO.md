# SteamRoller 0.2.0 Operator HOWTO

This document describes every SteamRoller command available in version 0.2.0.
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
0.2.0
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

## 12. Controlled single-host reboot

Interactive execution:

```bash
steamroller reboot ORION-LAB \
  --host velora-db-a01.ops.example \
  -sk foreman
```

The hostname must be an exact alias from the selected inventory. SteamRoller
asks the operator to type:

```text
REBOOT velora-db-a01.ops.example
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

- exactly one inventory host is accepted;
- active `dnf`, `yum`, or `rpm` blocks reboot;
- missing mandatory fstab mounts block reboot;
- PRE evidence is written before changing state;
- SSH return and boot-ID change are verified;
- mounts, kernel, uptime, and failed units are checked after reboot;
- newly failed units produce a failed result.

There is no `--all` reboot option in version 0.2.0.

## 13. Report status

```bash
steamroller status
```

Shows server, local execution time, UTC run ID, and operation type. Types
include `CONNECTIVITY`, `PRECHECK`, `REPO-OFF`, `REBOOT`, and incomplete runs.

Reports from a source checkout are stored in:

```text
reports/SERVER_NAME/RUN_ID/
```

## 14. Satellite environment expectations

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

## 15. Standalone Satellite diagnostic

Run directly on a managed host:

```bash
sudo ./scripts/test_satellite_check.sh
```

This is a focused diagnostic. The normal remote workflow is `steamroller
precheck`.

## 16. Exit behavior

- `0`: requested operation and fleet result succeeded;
- non-zero: invalid local configuration, unreachable host, failed check,
  cancelled reboot, Ansible failure, or failed post-operation validation.

Always inspect the final summary and referenced report directory before
continuing with maintenance.
