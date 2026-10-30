# SteamRoller setup utilities

This directory contains idempotent utilities for manual source installation,
reinstallation, migration, and future installation workflows.

## Source checkout PATH installation

Run as root from any SteamRoller source checkout:

```bash
./setup/manual/install-source-path.sh
source /root/.bashrc
steamroller version
strl version
```

Running the installer again updates the managed block without duplicating it.
The previous `.bashrc` is preserved with a timestamped
`.steamroller.bak.TIMESTAMP` suffix.
The same managed block loads Bash completion for commands, inventories,
inventory operations, common options, SSH key paths, and hostnames.
It also creates the managed short command:

```text
/usr/local/bin/strl -> PROJECT_ROOT/bin/steamroller
```

The installer refuses to replace an existing non-SteamRoller `strl` command.
Use `--short-command PATH` to select a different link path for testing or a
custom installation.

To remove only the managed SteamRoller entry:

```bash
./setup/manual/install-source-path.sh --remove
source /root/.bashrc
```

Removal deletes the `strl` link only when it still points to the current
SteamRoller checkout.
