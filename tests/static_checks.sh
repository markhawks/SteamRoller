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
    playbooks/15-repo-off.yml
    roles/connectivity/tasks/main.yml
    roles/precheck/tasks/main.yml
    roles/precheck/templates/precheck.txt.j2
    roles/repo_quarantine/tasks/main.yml
    scripts/render_summary.py
    scripts/show_config.py
    scripts/validate_config.py
    scripts/list_reports.py
    scripts/test_satellite_check.sh
    packaging/rpm/steamroller.spec
)

for required_file in "${required_files[@]}"; do
    [[ -f "$required_file" ]] || {
        printf 'Missing required file: %s\n' "$required_file" >&2
        exit 1
    }
done

if grep -REn --include='*.yml' --include='*.yaml' \
    'ansible\.builtin\.(dnf|yum|reboot):|(^|[[:space:]])(dnf|yum)[[:space:]]+(update|upgrade)' \
    playbooks roles; then
    printf 'Phase 1 must not contain patch or reboot actions.\n' >&2
    exit 1
fi

grep -q 'steamroller_registration_mode: auto' inventories/dev/group_vars/all.yml
grep -q 'steamroller_cluster_check_enabled: false' inventories/dev/group_vars/all.yml
grep -q '/opt/steamroller' packaging/rpm/steamroller.spec
grep -q '%config(noreplace)' packaging/rpm/steamroller.spec
grep -q -- '--private-key' bin/steamroller
grep -q -- '--ssh-key' bin/steamroller

bash -n bin/steamroller
bash -n scripts/test_satellite_check.sh
python3 -m py_compile scripts/render_summary.py
python3 -m py_compile scripts/show_config.py
python3 -m py_compile scripts/validate_config.py
python3 -m py_compile scripts/list_reports.py

printf 'Static checks passed.\n'
