# cti-pipeline

One repo, one container image, for the Claude-driven CTI automation components.
Sanitized GeneLabs reference build. Deploys to AWS or Azure from the same image.

## Layout
- `core/` — shared once: skill pack (`.claude/skills`), threatpipe MCP servers
  (`core/threatpipe`), doc-builder tools (`core/tools`), run scripts (`core/scripts`).
- `components/<name>/` — `task.md` (the prompt) + `component.yaml` (cadence, enabled
  MCP servers, output prefix). Components: bulletin-scan, perimeter-scan,
  threat-hunting, program-console, documentation-sync.
- `deploy/` — one `Dockerfile` and `entrypoint.sh`. `COMPONENT` selects the task,
  `CLOUD=aws|azure` selects where output goes.

## Model and secrets
Model is Claude on Amazon Bedrock in both clouds (Claude Code supports Bedrock and
Vertex, not Azure). Secrets are injected as env vars by the platform (Secrets Manager
on AWS, Key Vault on Azure); the run scripts prefer env per-credential, so no vault is
contacted. Never commit secrets.

## POC sources (free)
NVD, AlienVault OTX, abuse.ch, a news scraper, and Shodan (perimeter). Splunk is
shared infrastructure — ONE dev instance (Developer License), both clouds' egress IPs
allowlisted — used only by threat-hunting. Reporting engine is a separate Azure
Functions + OpenAI app and is not part of this image.

## Run one component locally
    COMPONENT=bulletin-scan ANTHROPIC_MODEL=<bedrock-profile> CLOUD=aws \
      OUTPUT_BUCKET=<bucket> deploy/entrypoint.sh

## Build once, deploy N times
    docker build -f deploy/Dockerfile -t cti-pipeline:poc .
Then one Fargate task (or Container Apps Job) per component, each with its own
`COMPONENT` and cadence. See deploy/aws and deploy/azure.
