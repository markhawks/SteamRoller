# SteamRoller 0.3.2 Release Notes

Release date: 2026-10-30

SteamRoller 0.3.2 adds Python 3.6 compatibility for experimental use of a
RHEL 8.6 or later control node. Managed hosts remain restricted to RHEL 9.x.

## Changed

- replaced `re.Pattern[...]`, built-in generic types, and PEP 604 unions with
  Python 3.6-compatible typing declarations;
- replaced newer `subprocess` convenience arguments with their Python 3.6
  equivalents;
- replaced `shlex.join` with a compatible quoted command builder;
- made inventory subcommand validation compatible with the RHEL 8 `argparse`;
- removed the newer PyYAML `sort_keys` dependency from inventory writes;
- added a Python 3.6 grammar check to the static test suite;
- added a complete RHEL 8.6+ installation mini-HOWTO to the README;
- added `openssh-clients` to the RPM runtime requirements.

## RHEL 8 control-node packages

```bash
dnf install -y \
  ansible-core \
  python3 \
  python3-pyyaml \
  git \
  openssh-clients \
  iputils \
  bash-completion
```

`ansible-core` requires RHEL 8.6 or later with the appropriate AppStream
content. RHEL 8 control-node support remains experimental until the complete
SteamRoller workflow has been validated there.

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
0.3.2
```

Review the complete operator guide in [HOWTO.md](HOWTO.md).
