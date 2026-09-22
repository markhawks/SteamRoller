# SteamRoller

<p align="center">
  <img src="docs/assets/steamroller-banner.jpeg"
       alt="SteamRoller automated RHEL validation"
       width="900">
</p>

SteamRoller is a conservative Ansible workflow for validating and, in later
phases, patching remote RHEL 9 systems. The control node may run RHEL 9 or
RHEL 10.

The current implementation is **Phase 1 only**:

- connectivity and privilege validation;
- read-only RHEL 9 prechecks;
- direct Red Hat CDN registration and repository checks;
- persistent per-host text and JSON evidence.

It does not update packages, reboot hosts, modify subscriptions, or perform
cluster/HA checks.

Repository configuration files are inspected by filename only. Files other
than those listed in `steamroller_allowed_repo_files` fail precheck by default.
Precheck never edits repository configuration. An operator may explicitly run
`steamroller repo-off ENVIRONMENT` to back up custom files into the protected
local report directory and then move them on the target beneath
`/etc/yum.repos.d/SteamRoller-RepoOff/RUN_ID/`.

## Development usage

Create a local inventory, which is intentionally ignored by Git:

```bash
cp inventories/dev/hosts.yml.example inventories/dev/hosts.yml
```

Edit `inventories/dev/hosts.yml`, then run:

```bash
./bin/steamroller doctor dev
./bin/steamroller connectivity dev
./bin/steamroller precheck dev
./bin/steamroller status
```

`steamroller status` displays one row per execution with the local execution
time, immutable run ID, operation type, and directory contents. Connectivity
runs and full precheck reports are identified explicitly even when the remote
hostname uses different capitalization between Ansible discovery methods.

Display the effective, non-sensitive defaults for an environment:

```bash
./bin/steamroller config dev
```

The wrapper automatically recognizes a source checkout. After RPM installation
the same commands use `/opt/steamroller` and `/etc/steamroller`.

Runtime reports and real customer inventories must never be committed. Clone
the repository at each customer site, create the local inventory from the
example, and keep customer-specific changes on a dedicated development branch.

Normal mode shows Ansible task progress followed by a fleet summary. Quiet mode
suppresses task progress but always shows the same final summary:

```bash
./bin/steamroller precheck dev --quiet
```

Use a non-default SSH private key without storing its path in the inventory:

```bash
./bin/steamroller connectivity dev --ssh-key /secure/path/steamroller_ed25519
./bin/steamroller precheck dev --quiet --ssh-key /secure/path/steamroller_ed25519
```

The equivalent environment variable is `STEAMROLLER_SSH_KEY`. The command-line
option takes precedence over the environment variable. Private keys must stay
outside the repository.

The summary contains one row for every inventory host. A host that is
unreachable or does not produce a report is displayed as `FAIL`, followed by
its error details. The command returns a non-zero exit status when any host
fails.

Reports are written beneath `reports/<server-name>/<run-id>/` by default. Override
the location with `steamroller_report_root`.

## Installed layout

The RPM installs application code in `/opt/steamroller`, configuration in
`/etc/steamroller`, reports in `/var/lib/steamroller/reports`, and exposes the
`steamroller` command through `/usr/bin`.

## License

Copyright (C) 2026 markhawks and SteamRoller contributors.

SteamRoller is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

SteamRoller is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See [LICENSE](LICENSE) for the complete terms.
