#!/usr/bin/bash
set -o errexit
set -o nounset
set -o pipefail

expected_name="${1:-}"
expected_environment="${2:-}"
if [[ $# -ge 2 ]]; then
    shift 2
else
    set --
fi
expected_repositories=("$@")

identity="$(subscription-manager identity 2>&1)" || {
    printf '%s\n' "SATELLITE CHECK: FAIL" "$identity" >&2
    exit 1
}
status="$(subscription-manager status 2>&1)" || true
repositories="$(subscription-manager repos --list-enabled 2>&1)" || {
    printf '%s\n' "SATELLITE CHECK: FAIL" "$repositories" >&2
    exit 1
}

consumer_name="$(printf '%s\n' "$identity" | awk -F':[[:space:]]*' '/^name:/{print $2; exit}')"
environment_name="$(printf '%s\n' "$identity" | awk -F':[[:space:]]*' '/^environment name:/{print $2; exit}')"
overall_status="$(printf '%s\n' "$status" | awk -F':[[:space:]]*' '/^Overall Status:/{print $2; exit}')"
if [[ "$status" == *"Simple Content Access"* ]]; then
    content_access_mode="Simple Content Access"
else
    content_access_mode="Entitlement-based"
fi
satellite_hostname="$(subscription-manager config --list | awk -F= '/^[[:space:]]*hostname[[:space:]]*=/{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit}')"

result=0
[[ -n "$consumer_name" ]] || result=1
[[ -n "$environment_name" ]] || result=1

if [[ -n "$expected_name" && "$consumer_name" != "$expected_name" ]]; then
    result=1
fi
if [[ -n "$expected_environment" && "$environment_name" != "$expected_environment" ]]; then
    result=1
fi

printf '%s\n' "SATELLITE REGISTRATION CHECK" "============================"
printf '%-24s %s\n' "Satellite server:" "${satellite_hostname:-unknown}"
printf '%-24s %s\n' "Name:" "${consumer_name:-missing}"
printf '%-24s %s\n' "Environment:" "${environment_name:-missing}"
printf '%-24s %s\n' "Registration status:" "$([[ -n "$consumer_name" ]] && printf Registered || printf 'Not registered')"
printf '%-24s %s\n' "Subscription status:" "${overall_status:-unknown}"
printf '%-24s %s\n' "Content access mode:" "$content_access_mode"
printf '\n%-8s %-70s %s\n' "RESULT" "REPOSITORY ID" "ENABLED"
printf '%-8s %-70s %s\n' "--------" "----------------------------------------------------------------------" "-------"

repository_count=0
current_repository=""
while IFS= read -r line; do
    case "$line" in
        "Repo ID:"*)
            current_repository="${line#Repo ID:}"
            current_repository="${current_repository#${current_repository%%[![:space:]]*}}"
            ;;
        "Enabled:"*)
            enabled="${line#Enabled:}"
            enabled="${enabled#${enabled%%[![:space:]]*}}"
            [[ -n "$current_repository" ]] || continue
            repository_count=$((repository_count + 1))
            if [[ "$enabled" == "1" ]]; then
                printf '%-8s %-70s %s\n' "PASS" "$current_repository" "$enabled"
            else
                printf '%-8s %-70s %s\n' "FAIL" "$current_repository" "$enabled"
                result=1
            fi
            current_repository=""
            ;;
    esac
done <<< "$repositories"

if [[ $repository_count -eq 0 ]]; then
    printf '%-8s %s\n' "FAIL" "No enabled repositories found"
    result=1
fi

for expected_repository in "${expected_repositories[@]}"; do
    if ! printf '%s\n' "$repositories" | awk -F':[[:space:]]*' -v expected="$expected_repository" '
        /^Repo ID:/ && $2 == expected { found = 1 }
        END { exit(found ? 0 : 1) }
    '; then
        printf '%-8s %s\n' "FAIL" "Missing expected repository: ${expected_repository}"
        result=1
    fi
done

printf '\nFINAL RESULT: %s\n' "$([[ $result -eq 0 ]] && printf PASS || printf FAIL)"
exit "$result"
