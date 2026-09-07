#!/usr/bin/env python3
"""Alternative runner using the Claude Agent SDK instead of the Claude Code CLI.

    pip install claude-agent-sdk python-dotenv
    python scripts/run_hunt_sdk.py

Reads .env, wires .mcp.json, points the agent at CTI_ROOT and the bundled skills,
and streams the task. This mirrors how Claude Desktop drove the scheduled task.
"""
import os, json, asyncio, pathlib
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Bedrock mode: the SDK reads these from the environment (set in .env).
os.environ.setdefault("CLAUDE_CODE_USE_BEDROCK", "1")
os.environ.pop("ANTHROPIC_API_KEY", None)  # never let an API key override Bedrock
# MCP credentials are resolved by the cti-feeds launchers from Key Vault (KEY_VAULT_URL);
# run `az login` first (or set AZURE_* in .env). Uncommented .env overrides are inherited.



CTI_ROOT = os.environ.get("CTI_ROOT")
if not CTI_ROOT:
    raise SystemExit("Set CTI_ROOT in .env")

prompt = (ROOT / "task" / "LOCAL_OVERRIDES.md").read_text() + "\n---\n" + \
         (ROOT / "task" / "cti-threat-hunting-task.md").read_text()
mcp = json.loads((ROOT / ".mcp.json").read_text()).get("mcpServers", {})

async def main():
    # SDK surface varies by version; see https://docs.claude.com/en/api/agent-sdk .
    from claude_agent_sdk import query, ClaudeAgentOptions
    options = ClaudeAgentOptions(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8"),
        mcp_servers=mcp,
        add_dirs=[CTI_ROOT, str(ROOT)],
        permission_mode="acceptEdits",
        setting_sources=["project"],   # loads ./.claude/skills
    )
    async for message in query(prompt=prompt, options=options):
        print(message)

if __name__ == "__main__":
    asyncio.run(main())
