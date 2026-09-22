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
- direct Red Hat CDN and Red Hat Satellite registration and repository checks;
- persistent per-host text and JSON evidence.

It does not update packages, reboot hosts, modify subscriptions, or perform
cluster/HA checks.

Repository configuration files are inspected by filename only. Files other
than those listed in `steamroller_allowed_repo_files` fail precheck by default.
Precheck never edits repository configuration. An operator may explicitly run
`steamroller repo-off ENVIRONMENT` to back up custom files into the protected
local report directory and then move them on the target beneath
`/etc/yum.repos.d/SteamRoller-RepoOff/RUN_ID/`.
Its final terminal summary lists the scanned directory, files left in place,
custom files found, local backup, remote quarantine, and files actually moved.

Repository quarantine can also be explicitly requested immediately before a
precheck:

```bash
steamroller precheck ENVIRONMENT --repo-off
```

This is a mutating opt-in operation: custom `.repo` files are backed up and
moved first, then the complete precheck runs against the resulting repository
configuration. Without `--repo-off`, precheck remains read-only.

## Development usage

Create an inventory by resolving and pinging every host before writing it:

```bash
./bin/steamroller inventory create -i AlfrescoDev \
  -h alfresco01.example.net -h alfresco02.example.net
```

SSH defaults to port `22` and user `root`; override them with `-p` and `-u`:

```bash
./bin/steamroller inventory add -i AlfrescoDev \
  -h alfresco03.example.net -p 2222 -u operator
./bin/steamroller inventory del -i AlfrescoDev \
  -h alfresco02.example.net -h alfresco03.example.net
./bin/steamroller inventory list
./bin/steamroller inventory list AlfrescoDev
```

For `create` and `add`, all hosts must answer ping before the inventory is
written; a failure leaves the existing data unchanged. Then run:

```bash
./bin/steamroller doctor dev
./bin/steamroller connectivity dev
./bin/steamroller precheck dev
./bin/steamroller status
```

`steamroller status` displays one row per execution with the local execution
time, immutable run ID, and operation type. Connectivity runs and full precheck
reports are identified explicitly even when the remote hostname uses different
capitalization between Ansible discovery methods.

Display the effective, non-sensitive defaults for an environment:

```bash
./bin/steamroller config dev
```

The wrapper automatically recognizes a source checkout. After RPM installation
the same commands use `/opt/steamroller` and `/etc/steamroller`.

Install the current source checkout in root's command `PATH` so that the
`./bin/` prefix is no longer required:

```bash
./setup/manual/install-source-path.sh
source /root/.bashrc
steamroller version
```

The installer is safe to run again after moving or reinstalling the source
checkout. It also enables Bash completion: type `steamroller` followed by
`Tab` twice to display commands and context-sensitive options. See
`setup/README.md` for removal and advanced options.

Runtime reports and real customer inventories must never be committed. Clone
the repository at each customer site, create the local inventory from the
example, and keep customer-specific changes on a dedicated development branch.

Normal mode shows Ansible task progress followed by a fleet summary. Quiet mode
(`-q` or `--quiet`) suppresses task progress but always shows the same final
summary:

```bash
steamroller precheck dev -q
```

Store private keys in ignored, named profiles beneath `ssh-keys/`. If exactly
one private key exists, SteamRoller selects it automatically. With multiple
profiles, use the short `-sk` selector; the private-key filename inside the
selected directory is discovered automatically:

```bash
mkdir -p ssh-keys/foreman
cp /secure/path/id_rsa_foreman_proxy ssh-keys/foreman/
chmod 700 ssh-keys ssh-keys/foreman
chmod 600 ssh-keys/foreman/id_rsa_foreman_proxy

steamroller connectivity dev -sk foreman
steamroller precheck dev -q -sk foreman
```

After `-sk` or `--ssh-key`, Bash completion lists the available profile
directories. Direct private-key paths remain supported. The equivalent
environment variable is `STEAMROLLER_SSH_KEY`; `STEAMROLLER_SSH_KEY_ROOT` can
override the managed directory. Private-key contents are never committed.

The standalone read-only Satellite discovery script remains available for
quick diagnostics:

```bash
sudo ./scripts/test_satellite_check.sh
```

Optional expected name, environment, and repository IDs can be supplied as
positional arguments.

The default `steamroller_registration_mode: auto` detects Satellite from the
RHSM server and environment returned by the managed host. A detected Satellite
is always reported and validated, including installations that still contain
the older `redhat_cdn` setting. Configure expected values in the optional environment file
`inventories/ENVIRONMENT/steamroller.yml` (create it from the example).
Precheck then validates the Satellite server, consumer name, Organization,
Lifecycle Environment, Content View, and enabled repository IDs. The terminal
report includes a dedicated `SATELLITE DETAILS` section after `HOST DETAILS`.
If no expected consumer name is configured, each consumer is validated against
that host's discovered FQDN, which supports inventories containing many hosts.
The discovered name, expected name, validation mode, and result remain visible
in `SATELLITE DETAILS` in both automatic and explicitly configured modes.

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
