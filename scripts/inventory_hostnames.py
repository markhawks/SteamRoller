#!/usr/bin/python3
"""Print canonical host aliases from an Ansible inventory."""

import argparse
import json
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--contains")
    args = parser.parse_args()
    try:
        result = subprocess.run(
            ["ansible-inventory", "-i", args.inventory, "--list"],
            check=True,
            capture_output=True,
            text=True,
        )
        hosts = sorted(json.loads(result.stdout).get("_meta", {}).get("hostvars", {}))
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"Unable to read inventory hosts: {error}", file=sys.stderr)
        return 2
    if args.contains is not None:
        return 0 if args.contains in hosts else 1
    for host in hosts:
        print(host)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
