# SteamRoller 0.3.1 Release Notes

Release date: 2026-09-23

SteamRoller 0.3.1 improves reboot operations and makes precheck guidance more
actionable while preserving explicit host selection and per-host evidence.

## Added

- sequential reboot of multiple explicitly selected inventory hosts;
- repeatable `--host HOST` option for the reboot command;
- one typed confirmation containing the complete ordered host list;
- Ansible `serial: 1` enforcement so hosts are never rebooted in parallel;
- duplicate-host rejection before reboot execution;
- complete suggested `steamroller reboot` command in precheck reports when
  uptime exceeds the configured warning threshold;
- preservation of the environment and SSH key selector in suggested commands;
- disk warnings showing percentage used, percentage free, free MiB, and total
  MiB.

## Multi-host reboot example

```bash
steamroller reboot ORION-LAB \
  --host velora-db-a01.ops.example \
  --host velora-db-a02.ops.example \
  -sk foreman
```

Interactive confirmation:

```text
REBOOT velora-db-a01.ops.example velora-db-a02.ops.example
```

There is no implicit `--all` mode. Every target must be named explicitly.
Each host receives independent PRE/POST evidence and validation.

## Precheck reporting example

```text
Uptime: 185 days [HIGH WARNING]
Suggested reboot command: steamroller reboot ORION-LAB --host velora-db-a01.ops.example -sk foreman
[WARNING] Filesystem /var is 91% used; 9% free (1843 MiB of 20480 MiB)
```

## Existing update safety

Version 0.3.1 retains the 0.3.0 interactive DNF workflow, audited force mode,
PostgreSQL unit protection, native DNF confirmation, post-update validation,
and suggested post-update reboot command.

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
0.3.1
```

Review the complete operator guide in [HOWTO.md](HOWTO.md).
