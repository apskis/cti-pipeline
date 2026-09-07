"""Verify that secrets-map.json entries resolve against Azure Key Vault.

Usage:
    uv run python scripts/fetch_secrets.py --list     # list vault secrets + map status
    uv run python scripts/fetch_secrets.py --check    # verify all mapped secrets resolve
"""
import argparse
import json
import os
import sys
from pathlib import Path

def get_vault_client():
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    vault_url = os.environ.get("KEY_VAULT_URL", "")
    if not vault_url:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("KEY_VAULT_URL="):
                    vault_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not vault_url:
        print("ERROR: KEY_VAULT_URL not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    credential = DefaultAzureCredential()
    return SecretClient(vault_url=vault_url, credential=credential), vault_url


def load_map():
    map_path = Path(__file__).resolve().parent.parent / "config" / "secrets-map.json"
    if not map_path.exists():
        print(f"ERROR: {map_path} not found", file=sys.stderr)
        sys.exit(1)
    data = json.loads(map_path.read_text())
    optional = set(data.pop("_optional", []))
    return {k: v for k, v in data.items() if not k.startswith("_")}, optional


def cmd_list():
    client, vault_url = get_vault_client()
    secret_map, optional = load_map()

    print(f"\nVault: {vault_url}")
    print(f"{'Secret name':<40} {'Mapped by':<30} {'Optional'}")
    print("-" * 80)

    vault_names = set()
    for prop in client.list_properties_of_secrets():
        vault_names.add(prop.name)

    reverse_map = {v: k for k, v in secret_map.items()}
    all_names = sorted(vault_names | set(secret_map.values()))

    for name in all_names:
        in_vault = name in vault_names
        env_var = reverse_map.get(name, "")
        is_opt = env_var in optional
        marker = "  " if in_vault else "MISSING"
        opt_marker = "yes" if is_opt else ""
        mapped = env_var if env_var else "(unmapped)"
        print(f"{'[' + marker + ']':<9} {name:<40} {mapped:<30} {opt_marker}")

    unmapped_vault = vault_names - set(secret_map.values())
    if unmapped_vault:
        print(f"\n{len(unmapped_vault)} vault secret(s) not in the map (may be unrelated).")


def cmd_check():
    client, vault_url = get_vault_client()
    secret_map, optional = load_map()

    print(f"\nVault: {vault_url}")
    print("Checking all mapped secrets...\n")

    ok = 0
    skipped = 0
    failed = 0

    for env_var, secret_name in sorted(secret_map.items()):
        is_opt = env_var in optional
        try:
            secret = client.get_secret(secret_name)
            if secret.value:
                print(f"  OK    {env_var:<35} -> {secret_name}")
                ok += 1
            else:
                print(f"  EMPTY {env_var:<35} -> {secret_name}  (value is empty)")
                failed += 1
        except Exception as e:
            if is_opt:
                print(f"  SKIP  {env_var:<35} -> {secret_name}  (optional, {e.__class__.__name__})")
                skipped += 1
            else:
                print(f"  FAIL  {env_var:<35} -> {secret_name}  ({e.__class__.__name__})")
                failed += 1

    print(f"\n{ok} resolved, {skipped} optional skipped, {failed} failed.")
    if failed == 0:
        print("All mapped credentials resolved. No values were printed.")
    else:
        print("Fix the failures above before running hunts.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Verify secrets-map against Azure Key Vault")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List vault secrets and map status")
    group.add_argument("--check", action="store_true", help="Verify all mapped secrets resolve")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.check:
        cmd_check()


if __name__ == "__main__":
    main()
