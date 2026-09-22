# SteamRoller 0.2.0 Release Notes

Release date: 2026-09-22

SteamRoller 0.2.0 is the first operational source release designed for
multi-host customer validation. It keeps package updates out of scope while
adding controlled, explicitly requested maintenance actions.

## Added

- inventory create, add, delete, and list commands;
- automatic hostname ping and IPv4 discovery;
- Bash completion for commands, environments, hosts, options, and SSH profiles;
- managed SSH key profiles and automatic private-key selection;
- multi-host operator summaries and improved report status listing;
- automatic Satellite detection and dedicated Satellite details;
- Simple Content Access-aware registration validation;
- repository file inspection, backup, and quarantine;
- optional `precheck --repo-off` workflow;
- PostgreSQL RPM inventory, Red Hat/PGDG classification, and update versions;
- controlled reboot of one exact inventory host;
- PRE/POST reboot evidence and validation;
- manual source PATH/completion installer.

## Changed

- disk blocking decisions use absolute free-space limits;
- `/` requires 4096 MiB free and `/boot` requires 400 MiB free;
- mandatory mounts are derived from `/etc/fstab`;
- additional `.repo` files fail precheck by default;
- failed hosts and unreachable hosts remain visible in fleet summaries;
- `-q` is an alias for `--quiet`;
- `-sk` is an alias for `--ssh-key` and accepts profile names.

## Safety boundaries

- package updates are not implemented;
- ordinary precheck remains read-only;
- repository changes require `repo-off` or `precheck --repo-off`;
- reboot requires one host and confirmation;
- fleet-wide reboot, cluster coordination, and application workflows are not
  implemented;
- private keys, customer inventories, reports, and backups remain outside Git.

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
0.2.0
```

Review the complete operator guide in [HOWTO.md](HOWTO.md).
