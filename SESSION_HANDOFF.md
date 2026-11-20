# SteamRoller Session Handoff

Prepared: 2026-11-20

## Current release

- Version: `0.3.3`
- Branch: `main`
- License: AGPL-3.0-or-later
- Source workflow validated primarily against real RHEL 9 systems.
- Managed-host policy: RHEL 7.0-7.9 assessment-only; RHEL 8.0-8.10 and RHEL
  9.x assessment/update.

## Latest completed work

- official `strl` short command with Bash completion;
- repeatable `--host` filtering for connectivity, precheck, and repository
  quarantine;
- RHEL 8 managed-host policy and Python 3.6-compatible control scripts;
- safe inode processing when Ansible omits inode facts;
- remote filesystems excluded from inode thresholds and listed in reports;
- detailed `dnf check` failures included in terminal summaries.
- dedicated audited acceptance of a known `dnf check` finding, with mandatory
  `dnf update --assumeno` validation and post-update comparison.
- RHEL 7 precheck through YUM, read-only `yum update --assumeno`, Satellite
  evidence, `kernel` RPM handling, and an explicit SteamRoller update block.

## Open operational investigation

- One Satellite-managed host reports its RHSM consumer name as an IPv4 address
  while the operating-system FQDN is a DNS name.
- SteamRoller correctly blocks the normal update because an empty
  `steamroller_expected_consumer_name` enables automatic FQDN comparison.
- Next session should compare `hostname -f`, DNS and `/etc/hosts`, RHSM facts,
  `subscription-manager identity`, and the Satellite Content Host UUID.
- Do not unregister or clean RHSM until the activation key, organization,
  lifecycle environment, content view, and possible duplicate Content Host
  have been verified.
- A per-host `steamroller_expected_consumer_name` override or audited `-F` update
  is available only after the IP-based consumer identity has been confirmed as
  intentional.

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
