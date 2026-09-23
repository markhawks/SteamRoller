# Bash completion for SteamRoller.

_steamroller_inventory_root() {
    local executable source_root
    executable="$(type -P steamroller 2>/dev/null)" || return
    source_root="$(cd "$(dirname "$executable")/.." 2>/dev/null && pwd)" || return
    if [[ -d "$source_root/inventories" ]]; then
        printf '%s\n' "$source_root/inventories"
    elif [[ -d /etc/steamroller/inventories ]]; then
        printf '%s\n' /etc/steamroller/inventories
    fi
}

_steamroller_inventories() {
    local root directory
    root="$(_steamroller_inventory_root)" || return
    for directory in "$root"/*; do
        [[ -f "$directory/hosts.yml" ]] && printf '%s\n' "${directory##*/}"
    done
}

_steamroller_key_root() {
    local executable source_root
    executable="$(type -P steamroller 2>/dev/null)" || return
    source_root="$(cd "$(dirname "$executable")/.." 2>/dev/null && pwd)" || return
    if [[ -d "$source_root/ssh-keys" ]]; then
        printf '%s\n' "$source_root/ssh-keys"
    elif [[ -d /etc/steamroller/ssh-keys ]]; then
        printf '%s\n' /etc/steamroller/ssh-keys
    fi
}

_steamroller_key_profiles() {
    local root directory
    root="$(_steamroller_key_root)" || return
    for directory in "$root"/*; do
        [[ -d "$directory" ]] && printf '%s\n' "${directory##*/}"
    done
}

_steamroller_inventory_hosts() {
    local environment="$1"
    local root inventory executable source_root
    root="$(_steamroller_inventory_root)" || return
    inventory="$root/$environment/hosts.yml"
    [[ -r "$inventory" ]] || return
    executable="$(type -P steamroller 2>/dev/null)" || return
    source_root="$(cd "$(dirname "$executable")/.." 2>/dev/null && pwd)" || return
    if [[ -x "$source_root/scripts/inventory_hostnames.py" || -r "$source_root/scripts/inventory_hostnames.py" ]]; then
        python3 "$source_root/scripts/inventory_hostnames.py" --inventory "$inventory" 2>/dev/null
    elif [[ -r /opt/steamroller/scripts/inventory_hostnames.py ]]; then
        python3 /opt/steamroller/scripts/inventory_hostnames.py --inventory "$inventory" 2>/dev/null
    fi
}

_steamroller_complete_inventory_action() {
    local subcommand="$1"
    local current="$2"
    case "$subcommand" in
        create)
            COMPREPLY=( $(compgen -W '-i --inventory -h --host -p --port -u --user --help' -- "$current") )
            ;;
        add)
            COMPREPLY=( $(compgen -W '-i --inventory -h --host -p --port -u --user --help' -- "$current") )
            ;;
        del)
            COMPREPLY=( $(compgen -W '-i --inventory -h --host --help' -- "$current") )
            ;;
        list)
            COMPREPLY=( $(compgen -W "$(_steamroller_inventories) --help" -- "$current") )
            ;;
    esac
}

_steamroller() {
    local current previous action inventory_action
    COMPREPLY=()
    current="${COMP_WORDS[COMP_CWORD]}"
    previous="${COMP_WORDS[COMP_CWORD-1]}"
    action="${COMP_WORDS[1]:-}"

    if (( COMP_CWORD == 1 )); then
        COMPREPLY=( $(compgen -W 'precheck connectivity repo-off reboot update config inventory doctor status version' -- "$current") )
        return
    fi

    case "$action" in
        precheck|connectivity|repo-off)
            if [[ "$previous" == "-sk" || "$previous" == "--ssh-key" ]]; then
                COMPREPLY=( $(compgen -W "$(_steamroller_key_profiles)" -- "$current") )
            elif (( COMP_CWORD == 2 )); then
                COMPREPLY=( $(compgen -W "$(_steamroller_inventories)" -- "$current") )
            else
                if [[ "$action" == "precheck" ]]; then
                    COMPREPLY=( $(compgen -W '-q --quiet --repo-off -sk --ssh-key' -- "$current") )
                else
                    COMPREPLY=( $(compgen -W '-q --quiet -sk --ssh-key' -- "$current") )
                fi
            fi
            ;;
        config|doctor)
            if (( COMP_CWORD == 2 )); then
                COMPREPLY=( $(compgen -W "$(_steamroller_inventories)" -- "$current") )
            fi
            ;;
        reboot)
            if [[ "$previous" == "-sk" || "$previous" == "--ssh-key" ]]; then
                COMPREPLY=( $(compgen -W "$(_steamroller_key_profiles)" -- "$current") )
            elif [[ "$previous" == "--host" ]]; then
                COMPREPLY=( $(compgen -W "$(_steamroller_inventory_hosts "${COMP_WORDS[2]:-}")" -- "$current") )
            elif (( COMP_CWORD == 2 )); then
                COMPREPLY=( $(compgen -W "$(_steamroller_inventories)" -- "$current") )
            else
                COMPREPLY=( $(compgen -W '--host -q --quiet -sk --ssh-key --confirm --timeout' -- "$current") )
            fi
            ;;
        update)
            if [[ "$previous" == "-sk" || "$previous" == "--ssh-key" ]]; then
                COMPREPLY=( $(compgen -W "$(_steamroller_key_profiles)" -- "$current") )
            elif [[ "$previous" == "--preserve-postgresql-unit" ]]; then
                COMPREPLY=( $(compgen -W 'backup restore' -- "$current") )
            elif [[ "$current" == --preserve-postgresql-unit=* ]]; then
                local mode_prefix="${current%%=*}="
                local mode_value="${current#*=}"
                COMPREPLY=( $(compgen -P "$mode_prefix" -W 'backup restore' -- "$mode_value") )
            elif [[ "$previous" == "--host" ]]; then
                COMPREPLY=( $(compgen -W "$(_steamroller_inventory_hosts "${COMP_WORDS[2]:-}")" -- "$current") )
            elif (( COMP_CWORD == 2 )); then
                COMPREPLY=( $(compgen -W "$(_steamroller_inventories)" -- "$current") )
            else
                COMPREPLY=( $(compgen -W '--host -sk --ssh-key -F --force --Force --preserve-postgresql-unit' -- "$current") )
            fi
            ;;
        inventory)
            if (( COMP_CWORD == 2 )); then
                COMPREPLY=( $(compgen -W 'create add del list' -- "$current") )
                return
            fi
            inventory_action="${COMP_WORDS[2]:-}"
            if [[ "$previous" == "-i" || "$previous" == "--inventory" ]]; then
                if [[ "$inventory_action" != "create" ]]; then
                    COMPREPLY=( $(compgen -W "$(_steamroller_inventories)" -- "$current") )
                fi
            elif [[ "$previous" == "-h" || "$previous" == "--host" ]]; then
                COMPREPLY=( $(compgen -A hostname -- "$current") )
            else
                _steamroller_complete_inventory_action "$inventory_action" "$current"
            fi
            ;;
    esac
}

complete -F _steamroller steamroller
complete -F _steamroller ./bin/steamroller
