# CLAUDE.md — cti-pipeline

Guidance Claude Code should read on every session in this repo.

## What this is
Sanitized GeneLabs build of April's CTI automation. One container image, seven
components (`components/<name>/`), switchable cloud (`CLOUD=aws|azure`) and model backend
(`MODEL_BACKEND=bedrock|subscription`). Shared core under `core/` (skills, threatpipe MCP
servers, tools). Deploy via `deploy/aws|azure/deploy-with-claude-code.md`. See
`docs/POC-overview.md`.

## Coding standards — apply them
Follow the **`coding-standards`** skill (`core/.claude/skills/coding-standards/`). Always
apply `rules/universal.md` and `rules/security.md`; add packs per stack.

For THIS repo (Python + Claude Code agent runtime): **universal + python + security**.
- Python 3.11+, full type hints, `uv` for envs and deps (this repo uses it), keep functions
  small, one responsibility, comment WHY not WHAT.
- Never commit secrets. Keys reach the pipeline as env from Secrets Manager / Key Vault.
- Sanitized brand is **GeneLabs**. Never introduce the real employer name into this repo.
- Do not modify working repos in place — this monorepo is the sanitized copy; keep it that way.

## Skills discovery
The pipeline loads skills from `core/` (`CLAUDE_PROJECT_DIR=/app/core`). For a local session
to see them, run `claude` from `core/` or set `CLAUDE_PROJECT_DIR=core`.

## Conventions
- Commit style: conventional commits (`feat:`, `fix:`, `docs:`, `chore:`), atomic commits.
- Generated deploy artifacts live under `deploy/*/generated/` (gitignored).
