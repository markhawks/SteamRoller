#!/usr/bin/bash
set -o errexit
set -o nounset
set -o pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DEFAULT_PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

project_root="$DEFAULT_PROJECT_ROOT"
bashrc_file="/root/.bashrc"
remove=false

usage() {
    printf '%s\n' \
        'Usage: install-source-path.sh [--project-root PATH] [--bashrc PATH] [--remove]' \
        '' \
        'Install or update a managed SteamRoller PATH entry in /root/.bashrc.' \
        'Use --remove to remove the managed entry.'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-root)
            [[ $# -ge 2 ]] || { printf 'Missing value after --project-root.\n' >&2; exit 2; }
            project_root="$2"
            shift 2
            ;;
        --bashrc)
            [[ $# -ge 2 ]] || { printf 'Missing value after --bashrc.\n' >&2; exit 2; }
            bashrc_file="$2"
            shift 2
            ;;
        --remove)
            remove=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

project_root="$(cd "$project_root" 2>/dev/null && pwd)" || {
    printf 'Project directory does not exist: %s\n' "$project_root" >&2
    exit 2
}
steamroller_bin="${project_root}/bin/steamroller"
[[ -x "$steamroller_bin" ]] || {
    printf 'SteamRoller executable not found: %s\n' "$steamroller_bin" >&2
    exit 2
}
completion_file="${project_root}/completions/steamroller.bash"
[[ -r "$completion_file" ]] || {
    printf 'SteamRoller Bash completion not found: %s\n' "$completion_file" >&2
    exit 2
}

if [[ "$bashrc_file" == "/root/.bashrc" && $EUID -ne 0 ]]; then
    printf 'Run this installer as root to modify /root/.bashrc.\n' >&2
    exit 2
fi

readonly begin_marker='# BEGIN SteamRoller managed PATH'
readonly end_marker='# END SteamRoller managed PATH'
bashrc_directory="$(dirname "$bashrc_file")"
[[ -d "$bashrc_directory" ]] || {
    printf 'Shell configuration directory does not exist: %s\n' "$bashrc_directory" >&2
    exit 2
}

if [[ ! -e "$bashrc_file" ]]; then
    install -m 0644 /dev/null "$bashrc_file"
fi
[[ -f "$bashrc_file" && -w "$bashrc_file" ]] || {
    printf 'Shell configuration is not a writable regular file: %s\n' "$bashrc_file" >&2
    exit 2
}

backup_file="${bashrc_file}.steamroller.bak.$(date -u +%Y%m%dT%H%M%S%NZ)"
cp -p -- "$bashrc_file" "$backup_file"
temporary_file="$(mktemp "${bashrc_directory}/.steamroller-bashrc.XXXXXX")"
trap 'rm -f "$temporary_file"' EXIT

awk -v begin="$begin_marker" -v end="$end_marker" '
    $0 == begin { managed = 1; next }
    $0 == end { managed = 0; next }
    !managed { print }
' "$bashrc_file" > "$temporary_file"

if [[ "$remove" == false ]]; then
    {
        printf '\n%s\n' "$begin_marker"
        printf 'export PATH="%s/bin:$PATH"\n' "$project_root"
        printf 'source "%s"\n' "$completion_file"
        printf '%s\n' "$end_marker"
    } >> "$temporary_file"
fi

chmod --reference="$bashrc_file" "$temporary_file"
chown --reference="$bashrc_file" "$temporary_file"
mv -f -- "$temporary_file" "$bashrc_file"
trap - EXIT

if [[ "$remove" == true ]]; then
    printf 'SteamRoller PATH entry removed from %s\n' "$bashrc_file"
else
    version="$(PATH="${project_root}/bin:${PATH}" steamroller version)"
    printf 'SteamRoller PATH installed successfully.\n'
    printf 'Project: %s\n' "$project_root"
    printf 'Shell configuration: %s\n' "$bashrc_file"
    printf 'Backup: %s\n' "$backup_file"
    printf 'Detected version: %s\n' "$version"
    printf 'Bash completion: enabled\n'
    printf '\nActivate it in the current shell with:\n'
    printf '  source %s\n' "$bashrc_file"
fi
