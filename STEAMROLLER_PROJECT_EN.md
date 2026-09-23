# Steamroller

**RHEL 9.x Remote Patching & Validation Automation**

## Scope

Steamroller automates remote patching of **Red Hat Enterprise Linux 9.x
only**.

Environment: - RHEL 9.3--9.8 hosts; current target RHEL 9.8 - Red Hat
Satellite provides repositories and Content Views - Ansible CLI is the
initial execution engine - Future migration to Ansible Automation
Platform / Automation Controller - No custom GUI - Initial rollout: DEV
/ RELEASE / TEST, then PROD

Do not add support for RHEL 7/8/10 or other distributions. Steamroller
must not bypass Satellite content management.

## Goal

Safe, repeatable, auditable workflow:

``` text
CONNECT -> PRECHECK -> SNAPSHOT -> PATCH -> REBOOT -> VALIDATE -> COMPARE -> REPORT
```

A blocking precheck failure must prevent patching. Store PRE/POST
evidence on the Ansible control node.

## Design

Use Ansible inventories, playbooks, reusable roles,
`group_vars`/`host_vars`, configuration variables and persistent
reports. Prefer Ansible modules over shell commands. Keep everything
compatible with future Automation Controller execution.

Suggested layout:

``` text
steamroller/
├── README.md
├── ansible.cfg
├── inventories/{dev,release,test,prod}/
├── playbooks/
├── roles/{connectivity,precheck,snapshot,patch,reboot,postcheck,report}/
├── group_vars/
├── host_vars/
├── config/
├── reports/
├── scripts/
└── docs/
```

Every check returns `PASS`, `WARNING`, `FAIL` or `SKIPPED`. Blocking
`FAIL` stops patching for that host.

# PRECHECK

The initial precheck must be completely read-only.

## Connectivity and privilege

Verify inventory membership, DNS/name resolution, SSH, key
authentication, expected Ansible user, `become`, and root command
execution. Failure is blocking.

## Host identity

Collect hostname, FQDN, IPs, environment/group, timestamp and unique run
ID.

## OS

Collect `/etc/redhat-release`, `/etc/os-release`, and
`rpm -q redhat-release`. Accept **RHEL 9.x only**. Any other OS/major
release is blocking.

## Kernel

Collect `uname -r` and installed kernels. Record running/newest kernel.
Running kernel older than newest installed kernel = warning.

## Uptime

Collect `uptime`, `uptime -s`, `who -b`. Configurable defaults: - \<90
days: PASS - 30--89: WARNING - 90--199: HIGH WARNING - \>=200:
CRITICAL WARNING

High uptime is visible but not automatically blocking.

## Satellite

Check `subscription-manager identity` and status. Verify expected
Satellite registration, Content View, Lifecycle Environment and
Organization.

``` yaml
expected_content_view: ""
expected_lifecycle_environment: ""
expected_organization: ""
```

Wrong registration/Content View = blocking. Steamroller must never
create, publish, promote or modify Content Views.

## Repositories

Collect `dnf repolist` and enabled repos. Verify required repos and
metadata access; detect DNS, proxy, TLS and repository errors. Failure
is blocking.

## Disk and inodes

Collect `df -hP` and `df -iP`. Check `/`, `/boot`, `/boot/efi` if
present, `/var`, `/var/log`, `/tmp`, and relevant local filesystems.

Configurable defaults: - \<80% PASS - 80--89% WARNING - 90--94% HIGH
WARNING - \>=95% FAIL

Also check absolute free space, `/boot` capacity for a new
kernel/initramfs, and inode exhaustion.

## Filesystems/mounts

Collect `findmnt`, `mount`, `lsblk`. Detect missing expected mounts,
unexpected read-only filesystems, failed mount units and relevant
`/etc/fstab` entries not mounted. Save state for POST comparison. Do not
perform invasive NFS/CIFS tests.

## DNF/RPM health

Run appropriate health checks such as `dnf check`. Detect broken
dependencies, incomplete transactions, RPM DB problems and concurrent
`dnf`/`yum`/`rpm` processes. Do not automatically repair RPM DB. Serious
errors/concurrency are blocking. `rpm -Va` may be optional because it is
noisy/expensive.

## Available updates

Use `dnf check-update`; exit code 100 means updates exist, not failure.
Save update list and summarize package count plus kernel/systemd/glibc
updates.

## Existing reboot requirement

If available, use `dnf needs-restarting -r`. Existing pending reboot =
visible warning.

## Services

Collect:

``` bash
systemctl --failed
systemctl list-units --type=service --state=running
systemctl list-unit-files --type=service --state=enabled
```

Save running, failed and enabled services. Services already failed PRE
must be documented.

Support configurable services:

``` yaml
critical_services: []
application_services: []
```

Do not hard-code application products.

## Processes/ports

Optionally save `ps -ef` and `ss -lntup` for diagnostic PRE/POST
comparison.

## Network

Collect `ip addr`, `ip route`, `ip link`, `nmcli device status`,
`nmcli connection show`. Verify management connectivity, expected
routing/DNS and Satellite reachability. Never modify network
configuration.

## Cluster/HA detection

Detect Pacemaker, Corosync, PCS and configurable HA indicators.

For v1:

``` text
CLUSTER DETECTED -> FAIL / MANUAL REVIEW
```

Never automatically patch/reboot cluster nodes in v1.

# PRE-PATCH SNAPSHOT

Save evidence on the control node:

``` text
reports/RUN_ID/HOSTNAME/
├── precheck.txt
├── os.txt
├── kernel.txt
├── uptime.txt
├── filesystem.txt
├── mounts.txt
├── services-running.txt
├── services-failed.txt
├── services-enabled.txt
├── processes.txt
├── ports.txt
├── network.txt
├── repositories.txt
├── updates-planned.txt
├── satellite.txt
└── summary.json
```

Never overwrite old runs. Never log secrets.

# Blocking conditions

Blocking examples: - SSH/become/root unavailable - unsupported OS -
invalid Satellite registration - wrong Content View/Lifecycle
Environment - required repos unavailable - insufficient disk, `/boot`,
or inodes - critical filesystem read-only - serious DNF/RPM failure -
package manager already active - cluster/HA detected - incomplete
mandatory precheck

Warnings include high uptime, pre-existing reboot requirement,
pre-existing failed services, old running kernel and disk warning
thresholds.

# Patch authorization

Support separate `PRECHECK` and `PATCH` execution. Require explicit
patch authorization such as:

``` yaml
patch_authorized: true
```

Avoid interactive prompts inside roles.

# PATCH

Use the appropriate Ansible DNF module, not `shell: dnf update -y`.

Record start/end time, duration, changed packages and failures.
Correctly handle "Nothing to do".

If patching fails:

``` text
FAILED PATCH
NO REBOOT
```

# Batching

Never patch the full inventory simultaneously. Use configurable
`serial`; initial default:

``` yaml
patch_serial: 1
```

# REBOOT

Use Ansible `reboot`. Record reboot start, loss/recovery of SSH and
duration. Use configurable timeout, initially 900 seconds. Host not
returning before timeout = `FAIL CRITICAL`.

# POSTCHECK

After reboot repeat relevant checks:

-   SSH/become/identity
-   RHEL release
-   running/installed kernel
-   boot time/uptime to confirm reboot
-   disk/inodes
-   filesystems/mounts
-   services
-   critical/application services
-   network/listening ports
-   Satellite registration/Content View/repos
-   DNF health and remaining updates

Compare actual identities, not only counts.

Critical examples:

``` text
RUNNING PRE -> NOT RUNNING POST
HEALTHY PRE -> FAILED POST
NEW FAILED SERVICE
MOUNT PRE -> MISSING POST
```

A configured critical service running PRE but down POST =
`FAIL CRITICAL`.

# PRE/POST comparison

Produce a concise automatic comparison:

``` text
HOST: quorin-node-a01.ops.example
OS:      RHEL 9.5 -> RHEL 9.8       PASS
KERNEL:  old -> new                  PASS
MOUNTS:  no missing mounts           PASS
SERVICES: new failed = 0             PASS
sshd:    RUNNING -> RUNNING          PASS
FINAL RESULT: SUCCESS
```

# Final status

Each host ends with exactly one primary result:

``` text
SUCCESS
SUCCESS WITH WARNINGS
FAILED PRECHECK
FAILED PATCH
FAILED REBOOT
FAILED POSTCHECK
```

Report host, environment, run ID, timestamps, OS/kernel PRE/POST, PRE
uptime, Content View, disk/inodes, DNF state, updated packages,
patch/reboot duration, services, warnings/errors and final result.

Produce at least `report.txt` and `summary.json`.

# Security

Never store passwords, Satellite tokens, sudo credentials, SSH private
keys or application credentials in Git. Support Ansible Vault initially
and Automation Controller credentials later. Use `no_log` where
required. Do not permanently disable SSH host-key checking.

# Configuration

Avoid hard-coded operational values:

``` yaml
target_rhel_minor: "9.8"
disk_warning_percent: 80
disk_critical_percent: 95
uptime_warning_days: 30
uptime_high_days: 90
uptime_critical_days: 200
reboot_timeout: 900
patch_serial: 1
expected_content_view: ""
expected_lifecycle_environment: ""
expected_organization: ""
critical_services: []
application_services: []
```

# Operator CLI

Operators may have limited Ansible knowledge. Optionally provide a thin
wrapper:

``` bash
./steamroller precheck test
./steamroller patch test
./steamroller status
```

The wrapper only validates arguments and orchestrates Ansible; it must
not duplicate patching logic. Make accidental PROD execution difficult.

# Out of scope for v1

-   non-RHEL9 systems
-   Satellite/Content View administration
-   automatic HA cluster patching
-   application configuration changes
-   automatic filesystem cleanup
-   automatic RPM DB repair
-   network changes
-   custom GUI
-   embedded credentials
-   hard-coded application-specific logic

# Roadmap

1.  **Discovery (complete):** repository structure, inventory, connectivity
    and read-only precheck.
2.  **Reporting (complete):** persistent PRE snapshots and JSON/text summaries.
3.  **DEV patching (in progress):** interactive single-host DNF and controlled
    reboot are implemented; dedicated postcheck remains pending.
4.  **Comparison:** automatic PRE/POST validation.
5.  **RELEASE/TEST:** larger inventory validation.
6.  **Production hardening:** approvals, batches, failure strategy,
    documentation/integrations.
7.  **Automation Controller:** reuse the same
    repository/playbooks/roles/configuration.

# Initial implementation milestone (completed)

The original Phase 1 requirement was:

Required commands:

``` bash
ansible-playbook -i inventories/dev/hosts.yml playbooks/00-connectivity.yml
ansible-playbook -i inventories/dev/hosts.yml playbooks/10-precheck.yml
```

`10-precheck.yml` must be read-only, return per-host
`PASS/WARNING/FAIL`, and persist reports on the control node.

This gate has been satisfied: the precheck and controlled reboot were validated
on real test systems before interactive DNF update was added. Current update
execution remains single-host, requires the native DNF confirmation, never
reboots automatically, and can protect a customized PostgreSQL systemd unit.

# Core principle

Steamroller is not successful merely because `dnf update` exits
successfully.

Success means the host had a known valid PRE state, passed mandatory
safety checks, patched successfully, rebooted successfully, and returned
to an acceptable POST state with documented PRE/POST differences.
