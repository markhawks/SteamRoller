# SteamRoller setup utilities

This directory contains idempotent utilities for manual source installation,
reinstallation, migration, and future installation workflows.

## Source checkout PATH installation

Run as root from any SteamRoller source checkout:

```bash
./setup/manual/install-source-path.sh
source /root/.bashrc
steamroller version
```

Running the installer again updates the managed block without duplicating it.
The previous `.bashrc` is preserved with a timestamped
`.steamroller.bak.TIMESTAMP` suffix.

To remove only the managed SteamRoller entry:

```bash
./setup/manual/install-source-path.sh --remove
source /root/.bashrc
```
