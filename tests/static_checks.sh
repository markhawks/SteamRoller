#!/usr/bin/bash
set -o errexit
set -o nounset
set -o pipefail

readonly project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

required_files=(
    ansible.cfg
    bin/steamroller
    inventories/dev/hosts.yml
    inventories/dev/steamroller.yml.example
    playbooks/00-connectivity.yml
    playbooks/10-precheck.yml
    playbooks/11-precheck-repo-off.yml
    playbooks/15-repo-off.yml
    playbooks/20-reboot.yml
    roles/connectivity/tasks/main.yml
    roles/precheck/tasks/main.yml
    roles/precheck/templates/precheck.txt.j2
    roles/repo_quarantine/tasks/main.yml
    roles/reboot_host/tasks/main.yml
    scripts/render_summary.py
    scripts/show_config.py
    scripts/validate_config.py
    scripts/list_reports.py
    scripts/manage_inventory.py
    scripts/resolve_ssh_key.py
    scripts/inventory_hostnames.py
    scripts/run_dnf_update.py
    scripts/test_satellite_check.sh
    setup/manual/install-source-path.sh
    setup/README.md
    completions/steamroller.bash
    ssh-keys/README.md
    docs/HOWTO.md
    docs/RELEASE_NOTES_0.2.0.md
    docs/RELEASE_NOTES_0.3.0.md
    packaging/rpm/steamroller.spec
    tests/test_dnf_update.py
)

for required_file in "${required_files[@]}"; do
    [[ -f "$required_file" ]] || {
        printf 'Missing required file: %s\n' "$required_file" >&2
        exit 1
    }
done

forbidden_identifiers='mena''rini|mcd''lnx|mcd''l|rh98''virt|server0''[1-9]|app0''[1-9]|alfresco-''dev|ipm-''dev'
if grep -REin \
    "$forbidden_identifiers" \
    README.md PROJECT_STATUS.md STEAMROLLER_PROJECT_EN.md docs \
    tests/test_inventory_manager.py tests/test_ssh_key_resolver.py; then
    printf 'Documentation or tests contain forbidden customer or legacy host identifiers.\n' >&2
    exit 1
fi

if grep -REn --include='*.yml' --include='*.yaml' \
    'ansible\.builtin\.(dnf|yum):|(^|[[:space:]])(dnf|yum)[[:space:]]+(update|upgrade)' \
    playbooks roles; then
    printf 'Phase 1 must not contain package update actions.\n' >&2
    exit 1
fi

reboot_action_files="$(grep -REl --include='*.yml' --include='*.yaml' \
    'ansible\.builtin\.reboot:' playbooks roles || true)"
[[ "$reboot_action_files" == "roles/reboot_host/tasks/main.yml" ]] || {
    printf 'Reboot actions are permitted only in the controlled reboot role.\n' >&2
    exit 1
}

grep -q 'steamroller_registration_mode: auto' inventories/dev/group_vars/all.yml
grep -q 'steamroller_cluster_check_enabled: false' inventories/dev/group_vars/all.yml
grep -q '/opt/steamroller' packaging/rpm/steamroller.spec
grep -q '%config(noreplace)' packaging/rpm/steamroller.spec
grep -q -- '--private-key' bin/steamroller
grep -q -- '--ssh-key' bin/steamroller
grep -q -- '-q|--quiet' bin/steamroller
grep -q -- 'reboot ENVIRONMENT --host HOST' bin/steamroller
grep -q -- 'update ENVIRONMENT --host HOST' bin/steamroller
grep -q -- '--preserve-postgresql-unit' bin/steamroller
grep -q -- '-F|--force|--Force' bin/steamroller
grep -q 'Suggested reboot command' scripts/render_summary.py
grep -q 'POSTGRESQL DETAILS' roles/precheck/templates/precheck.txt.j2
grep -q 'postgresql.txt' roles/precheck/tasks/main.yml
grep -qx '0.3.0' VERSION
grep -q '^Version:[[:space:]]*0.3.0$' packaging/rpm/steamroller.spec
grep -q 'Current version: \*\*0.3.0\*\*' README.md
[[ -x setup/manual/install-source-path.sh ]]

bash -n bin/steamroller
bash -n scripts/test_satellite_check.sh
bash -n setup/manual/install-source-path.sh
bash -n completions/steamroller.bash
python3 -m py_compile scripts/render_summary.py
python3 -m py_compile scripts/show_config.py
python3 -m py_compile scripts/validate_config.py
python3 -m py_compile scripts/list_reports.py
python3 -m py_compile scripts/manage_inventory.py
python3 -m py_compile scripts/resolve_ssh_key.py
python3 -m py_compile scripts/inventory_hostnames.py
python3 -m py_compile scripts/run_dnf_update.py
python3 scripts/inventory_hostnames.py --inventory inventories/dev/hosts.yml | grep -q .
python3 -m unittest tests/test_inventory_manager.py
python3 -m unittest tests/test_ssh_key_resolver.py
python3 -m unittest tests/test_dnf_update.py

printf 'Static checks passed.\n'
