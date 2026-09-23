# SteamRoller 0.3.0 Release Notes

Release date: 2026-09-23

SteamRoller 0.3.0 introduces an operator-controlled package update workflow
while retaining the single-host safety boundary and persistent audit evidence.

## Added

- interactive `steamroller update ENVIRONMENT --host HOST` command;
- complete precheck immediately before every update;
- native DNF transaction display and manual `[y/N]` confirmation;
- post-update DNF, kernel, reboot-required, remaining-update, and systemd checks;
- complete DNF transaction log, DNF history, JSON summary, and text postcheck;
- final suggested `steamroller reboot` command for the updated host;
- optional protection of a customized
  `/usr/lib/systemd/system/postgresql.service`;
- PostgreSQL unit `backup` and explicit `restore` modes;
- local and remote PostgreSQL unit backups, metadata, checksums, and unified diff;
- checksum, `daemon-reload`, and `systemd-analyze verify` validation after restore;
- audited `-F`, `--force`, and `--Force` update authorization;
- typed `FORCE UPDATE HOST` confirmation and explicit overridden-finding report;
- Bash completion for update environments, hosts, SSH profiles, force options,
  and PostgreSQL protection modes;
- `DNF-UPDATE` classification in `steamroller status`.

## Force-mode safety

Force mode can override reviewed policy findings, including a mandatory fstab
mount reported as read-only. A forced run is always at least `WARNING`.

It cannot bypass missing mandatory mounts, read-only critical filesystems,
insufficient disk space or inodes, unsupported operating systems, failed
mandatory collection, DNF/RPM health or concurrency failures, or unavailable
required repositories.

## PostgreSQL unit protection

`--preserve-postgresql-unit backup` retains the original unit and reports any
change without replacing the vendor file. `restore` copies back only a unit
identified as customized, then reloads systemd and validates the result.
SteamRoller never restarts PostgreSQL automatically.

The long-term recommendation remains migration of local settings to:

```text
/etc/systemd/system/postgresql.service.d/override.conf
```

## Safety boundaries

- update and reboot target exactly one inventory host;
- update always requires an interactive terminal and native DNF confirmation;
- forced updates require a second, host-specific typed confirmation;
- update never triggers reboot automatically;
- unattended fleet updates, multi-host reboot, and cluster/HA orchestration are
  not implemented;
- private keys, inventories, reports, and backups remain outside Git.

## Upgrade from a source checkout

```bash
cd /root/SteamRoller
git pull
./setup/manual/install-source-path.sh
source /root/.bashrc
steamroller version
```

Expected output:

```text
0.3.0
```

Review the complete operator guide in [HOWTO.md](HOWTO.md).
