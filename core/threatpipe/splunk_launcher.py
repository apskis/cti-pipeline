"""Launcher for splunk-mcp-server that fetches the auth header from Key Vault.

Claude Desktop runs this instead of npx mcp-remote directly. This script:
1. Fetches the Splunk auth header from Azure Key Vault
2. Launches mcp-remote with the header injected and --port 0 so each
   instance picks a random free port (avoids callback-port collisions when
   Claude Desktop spawns multiple copies for its shared pool)
"""

import os
import sys
import subprocess


def main():
    vault_url = os.environ.get("KEY_VAULT_URL", "").strip()
    if not vault_url:
        print("KEY_VAULT_URL not set, cannot fetch credentials", file=sys.stderr)
        sys.exit(1)

    auth_header = os.environ.get("AUTH_HEADER", "").strip()

    if not auth_header:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
            secret = client.get_secret("splunk-auth-header")
            auth_header = secret.value
            print("Loaded Splunk auth header from vault", file=sys.stderr)

        except Exception as e:
            print(f"Key Vault unavailable ({type(e).__name__}), "
                  "cannot load Splunk credentials", file=sys.stderr)
            sys.exit(1)

    sys.exit(subprocess.call([
        "cmd", "/c", "npx", "-y", "mcp-remote@latest",
        os.environ.get("SPLUNK_MCP_URL",
            "https://es.<your-stack>.splunkcloud.com/en-US/splunkd/__raw/services/mcp"),
        "--header", f"Authorization:{auth_header}",
        "--port", "0",
    ]))


if __name__ == "__main__":
    main()
