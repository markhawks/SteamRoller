# SteamRoller Session Handoff

Prepared: 2026-11-02

## Current release

- Version: `0.3.3`
- Branch: `main`
- License: AGPL-3.0-or-later
- Source workflow validated primarily against real RHEL 9 systems.
- Managed-host policy: RHEL 8.0-8.10 and RHEL 9.x.

## Latest completed work

- official `strl` short command with Bash completion;
- repeatable `--host` filtering for connectivity, precheck, and repository
  quarantine;
- RHEL 8 managed-host policy and Python 3.6-compatible control scripts;
- safe inode processing when Ansible omits inode facts;
- remote filesystems excluded from inode thresholds and listed in reports;
- detailed `dnf check` failures included in terminal summaries.

## Verification

Run before continuing development:

```bash
bash tests/static_checks.sh
ansible-playbook --syntax-check playbooks/00-connectivity.yml
ansible-playbook --syntax-check playbooks/10-precheck.yml
ansible-playbook --syntax-check playbooks/15-repo-off.yml
```

## Next priorities

1. Validate the complete workflow against representative RHEL 8 managed hosts.
2. Validate PostgreSQL unit `backup` and `restore` on a non-production host.
3. Expand negative-path testing for DNF locks and damaged RPM dependencies.
4. Build and test the first RPM on clean RHEL 9 and RHEL 10 systems.
5. Define report retention and backup policy.

Do not commit real inventories, reports, repository backups, or private SSH
keys. Runtime and customer-specific paths are already covered by `.gitignore`.
