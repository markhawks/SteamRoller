# SteamRoller 0.3.3 Release Notes

Release date: 2026-11-02

SteamRoller 0.3.3 improves targeted fleet assessment and makes filesystem and
DNF failures more accurate and actionable.

## Added

- repeatable `--host HOST` selection for `connectivity`, `precheck`, and
  `repo-off`;
- inventory-aware Bash completion after `--host`;
- validation that every selected host belongs to the requested environment;
- explicit reporting of remote mounts excluded from inode thresholds;
- detailed `dnf check` output in the terminal summary, including package and
  missing-library information;
- regression tests for incomplete inode facts, remote NFS mounts, and DNF
  dependency diagnostics.

## Changed

- targeted check execution and final reports now contain only explicitly
  selected hosts;
- inode warning and failure thresholds apply only to local filesystems;
- NFS, NFS4, CIFS, SMB3, Ceph, GlusterFS, SSHFS, and 9p mounts are excluded
  from inode classification while remaining visible as evidence;
- mounts without `inode_total` or `inode_used` facts are safely ignored instead
  of aborting the precheck;
- managed-host policy supports RHEL 8.0 through 8.10 and RHEL 9.x.

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
0.3.3
```

Review the complete operator guide in [HOWTO.md](HOWTO.md).
