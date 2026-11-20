# SteamRoller 0.3.4 Release Notes

Release date: 2026-11-20

SteamRoller 0.3.4 adds read-only RHEL 7 assessment and correlates package
dependency findings with a non-mutating update simulation.

## Added

- read-only precheck support for RHEL 7.0 through RHEL 7.9;
- automatic YUM selection and `kernel` RPM discovery on RHEL 7;
- `yum update --assumeno` evidence and dependency-resolution status;
- explicit terminal and report notice that SteamRoller update is unsupported
  on RHEL 7;
- package-provider guidance using `rpm --whatprovides` and `yum/dnf provides`;
- separate warning when a registered host reports that it is not receiving
  update content;
- repository-wide privacy checks for known customer identifiers in all
  publishable source paths.

## Changed

- package health checks now use YUM on RHEL 7 and DNF on RHEL 8/9;
- `rpm -q --whatprovides system-release` supports release-package variants;
- kernel discovery uses `kernel` on RHEL 7 and `kernel-core` on RHEL 8/9;
- `yum/dnf check` findings are warnings when the corresponding
  `update --assumeno` resolves a valid transaction;
- a failed update simulation remains a blocking precheck failure;
- DNF updates with accepted dependency findings continue to require
  `--allow-dnf-check-failure`, typed confirmation, and audit evidence;
- package-manager plugin noise is filtered from the terminal summary while
  complete raw output remains in report evidence.

## RHEL 7 safety boundary

RHEL 7 support is assessment-only. These commands remain read-only with
respect to installed packages:

```bash
yum -q check
yum -q check-update
yum update --assumeno
```

`steamroller update` accepts only RHEL 8 and RHEL 9 managed hosts.

## Upgrade from a source checkout

```bash
cd /root/SteamRoller
git pull
./setup/manual/install-source-path.sh
source /root/.bashrc
strl version
```

Expected output:

```text
0.3.4
```

Review the complete operator guide in [HOWTO.md](HOWTO.md).
