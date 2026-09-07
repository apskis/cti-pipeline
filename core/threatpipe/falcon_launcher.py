"""Launcher for falcon-mcp that fetches CrowdStrike credentials from Key Vault.

Claude Desktop runs this instead of falcon-mcp directly. This script:
1. Fetches Falcon credentials from Azure Key Vault
2. Sets them as environment variables
3. Launches falcon-mcp (via uvx) with those vars in the environment
"""

import os
import sys
import subprocess


def main():
    vault_url = os.environ.get("KEY_VAULT_URL", "").strip()
    if not vault_url:
        print("KEY_VAULT_URL not set, cannot fetch credentials", file=sys.stderr)
        sys.exit(1)

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        from azure.core.exceptions import ResourceNotFoundError

        client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())

        secret_map = {
            "FALCON_CLIENT_ID": "falcon-client-id",
            "FALCON_CLIENT_SECRET": "falcon-client-secret",
            "FALCON_BASE_URL": "falcon-base-url",
        }

        for env_name, secret_name in secret_map.items():
            if not os.environ.get(env_name):
                try:
                    val = client.get_secret(secret_name).value
                    if val:
                        os.environ[env_name] = val
                        print(f"Loaded {env_name} from vault", file=sys.stderr)
                except ResourceNotFoundError:
                    print(f"Secret {secret_name} not found in vault", file=sys.stderr)
                except Exception as e:
                    print(f"Cannot read {secret_name}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"Key Vault unavailable ({type(e).__name__}), "
              "falling back to environment", file=sys.stderr)

    # Launch falcon-mcp via uvx
    sys.exit(subprocess.call(["uvx", "falcon-mcp"]))


if __name__ == "__main__":
    main()
