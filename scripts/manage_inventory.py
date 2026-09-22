#!/usr/bin/python3
"""Create, update, and display SteamRoller Ansible inventories."""

import argparse
import ipaddress
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml


NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
HOST_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class InventoryError(Exception):
    """Operator-facing inventory error."""


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="steamroller inventory", add_help=False)
    root.add_argument("--help", action="help", help="show this help message and exit")
    root.add_argument("--inventory-root", required=True, help=argparse.SUPPRESS)
    commands = root.add_subparsers(dest="command", required=True)

    for command in ("create", "add"):
        item = commands.add_parser(command, add_help=False)
        item.add_argument("--help", action="help")
        item.add_argument("-i", "--inventory", required=True)
        item.add_argument("-h", "--host", action="append", required=True)
        item.add_argument("-p", "--port", type=int, default=22)
        item.add_argument("-u", "--user", default="root")

    delete = commands.add_parser("del", add_help=False)
    delete.add_argument("--help", action="help")
    delete.add_argument("-i", "--inventory", required=True)
    delete.add_argument("-h", "--host", action="append", required=True)

    listing = commands.add_parser("list", add_help=False)
    listing.add_argument("--help", action="help")
    listing.add_argument("inventory", nargs="?")
    return root


def validate_name(value: str, label: str, pattern: re.Pattern[str]) -> None:
    if not pattern.fullmatch(value):
        raise InventoryError(f"Invalid {label}: {value}")


def inventory_path(root: Path, name: str) -> Path:
    validate_name(name, "inventory name", NAME_PATTERN)
    return root / name / "hosts.yml"


def resolve_host(host: str) -> str:
    validate_name(host, "host name", HOST_PATTERN)
    try:
        probe = subprocess.run(
            ["ping", "-c", "1", "-W", "2", "--", host],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError as error:
        raise InventoryError("ping command is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise InventoryError(f"Ping timeout: {host}") from error
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout).strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise InventoryError(f"Host does not answer ping: {host}{suffix}")
    first_line = probe.stdout.splitlines()[0] if probe.stdout.splitlines() else ""
    candidates = re.findall(r"\(([^()]*)\)", first_line)
    candidates.extend(first_line.split())
    for candidate in candidates:
        candidate = candidate.strip("():")
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.version == 4:
            return str(address)
    raise InventoryError(f"Ping succeeded but returned no IPv4 address for {host}")


def load_inventory(path: Path, name: str) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        raise InventoryError(f"Unable to read inventory {path}: {error}") from error
    try:
        hosts = data["all"]["children"][name]["hosts"]
    except (KeyError, TypeError) as error:
        raise InventoryError(
            f"Inventory {path} does not contain all.children.{name}.hosts"
        ) from error
    if not isinstance(hosts, dict):
        raise InventoryError(f"Invalid hosts mapping in {path}")
    return data


def new_inventory(name: str) -> dict:
    return {"all": {"children": {name: {"hosts": {}}}}}


def hosts_mapping(data: dict, name: str) -> dict:
    return data["all"]["children"][name]["hosts"]


def write_inventory(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".hosts.yml.", dir=path.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("---\n")
            yaml.safe_dump(data, stream, sort_keys=False, default_flow_style=False)
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def unique_hosts(values: list[str]) -> list[str]:
    hosts = list(dict.fromkeys(values))
    for host in hosts:
        validate_name(host, "host name", HOST_PATTERN)
    return hosts


def resolve_all(hosts: list[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for host in hosts:
        print(f"Resolving and pinging {host} ...", flush=True)
        resolved[host] = resolve_host(host)
        print(f"  PASS {host} -> {resolved[host]}")
    return resolved


def create_or_add(args: argparse.Namespace, root: Path) -> None:
    name = args.inventory
    path = inventory_path(root, name)
    if not 1 <= args.port <= 65535:
        raise InventoryError("SSH port must be between 1 and 65535")
    if not args.user or any(character.isspace() for character in args.user):
        raise InventoryError(f"Invalid SSH user: {args.user!r}")
    hosts = unique_hosts(args.host)
    if args.command == "create":
        if path.exists():
            raise InventoryError(f"Inventory already exists: {name}")
        data = new_inventory(name)
    else:
        if not path.is_file():
            raise InventoryError(f"Inventory does not exist: {name}")
        data = load_inventory(path, name)
    configured = hosts_mapping(data, name)
    duplicates = [host for host in hosts if host in configured]
    if duplicates:
        raise InventoryError(f"Hosts already present: {', '.join(duplicates)}")

    resolved = resolve_all(hosts)
    for host in hosts:
        configured[host] = {
            "ansible_host": resolved[host],
            "ansible_user": args.user,
            "ansible_port": args.port,
        }
    write_inventory(path, data)
    verb = "created" if args.command == "create" else "updated"
    print(f"Inventory {verb}: {name}")
    print(f"Hosts added: {len(hosts)}")
    print(f"File: {path}")


def delete_hosts(args: argparse.Namespace, root: Path) -> None:
    name = args.inventory
    path = inventory_path(root, name)
    if not path.is_file():
        raise InventoryError(f"Inventory does not exist: {name}")
    data = load_inventory(path, name)
    configured = hosts_mapping(data, name)
    hosts = unique_hosts(args.host)
    missing = [host for host in hosts if host not in configured]
    if missing:
        raise InventoryError(f"Hosts not present: {', '.join(missing)}")
    for host in hosts:
        del configured[host]
    write_inventory(path, data)
    print(f"Inventory updated: {name}")
    print(f"Hosts removed: {len(hosts)}")
    print(f"File: {path}")


def list_inventories(root: Path) -> None:
    names = sorted(path.parent.name for path in root.glob("*/hosts.yml") if path.is_file())
    print("INVENTORY")
    print("------------------------------")
    if names:
        for name in names:
            print(name)
    else:
        print("No inventories found")


def list_hosts(root: Path, name: str) -> None:
    path = inventory_path(root, name)
    if not path.is_file():
        raise InventoryError(f"Inventory does not exist: {name}")
    configured = hosts_mapping(load_inventory(path, name), name)
    print(f"Inventory: {name}")
    print(f"{'HOST':<40} IP ADDRESS")
    print(f"{'-' * 40} {'-' * 39}")
    if not configured:
        print("No hosts configured")
        return
    for host, variables in configured.items():
        address = variables.get("ansible_host", "-") if isinstance(variables, dict) else "-"
        print(f"{host:<40} {address}")


def main() -> int:
    args = parser().parse_args()
    root = Path(args.inventory_root)
    try:
        if args.command in {"create", "add"}:
            create_or_add(args, root)
        elif args.command == "del":
            delete_hosts(args, root)
        elif args.inventory:
            list_hosts(root, args.inventory)
        else:
            list_inventories(root)
    except InventoryError as error:
        print(f"INVENTORY FAIL: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
