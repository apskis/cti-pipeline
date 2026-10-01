# cti-pipeline

One repo, one container image, for the Claude-driven CTI automation components.
Sanitized GeneLabs reference build. Deploys to AWS or Azure from the same image.

## Layout
- `core/` — shared once: skill pack (`.claude/skills`), threatpipe MCP servers
  (`core/threatpipe`), doc-builder tools (`core/tools`), run scripts (`core/scripts`).
- `components/<name>/` — `task.md` (the prompt) + `component.yaml` (cadence, enabled
  MCP servers, output prefix). Components: bulletin-scan, perimeter-scan,
  threat-hunting, reporting, program-console, documentation-sync.
- `deploy/` — one `Dockerfile` and `entrypoint.sh`. `COMPONENT` selects the task,
  `CLOUD=aws|azure` selects where output goes.

## Model backend (switchable)
`MODEL_BACKEND` selects the runtime:
- `bedrock` (default): Claude on Amazon Bedrock. AWS creds come from the task role, so
  no key is injected. `ANTHROPIC_MODEL` is the Bedrock inference-profile id
  (e.g. `us.anthropic.claude-sonnet-4-5-20250929-v1:0`). This is the cloud deployment.
- `subscription`: Claude Code on a Pro/Max plan via a long-lived OAuth token from
  `claude setup-token`, injected as `CLAUDE_CODE_OAUTH_TOKEN`. Set `ANTHROPIC_MODEL=opus`
  to pin Opus. Use this locally / on demand; do not ship a personal token into an
  always-on cloud cron.

Claude Code supports Bedrock and Vertex, not Azure, so on Azure compute the Bedrock
backend still calls Bedrock cross-cloud.

## Cost controls
Model tokens are most of the bill, so the defaults keep them down:
- **Builder passes on Haiku.** `BUILD_MODEL` (default Haiku 4.5 on either backend) runs the
  template filling passes; the scan keeps `ANTHROPIC_MODEL`. Set `BUILD_MODEL=$ANTHROPIC_MODEL`
  to undo. `BUILD_PASSES` (default 2) and `BUILD_BATCH` (default 4) cap builder sessions per
  run; anything left builds on the next run.
- **No model for program-console.** It is a plain Python refresh, so the entrypoint never
  starts a Claude session for it.
- **Cost per run is logged.** Every session prints a `[cost]` line (cost, turns, tokens,
  cache reads) and appends it to `state/cost-log.jsonl`, which ships with the run state.
  On `subscription` the dollar figure is the API price equivalent, not a bill.
- **POC cadence.** bulletin-scan runs Mon/Wed/Fri; its research window starts at the previous
  scan report, so the skipped days are still covered.
- **Lean scan prompt.** Rules for connectors the cloud run does not enable live in
  `components/bulletin-scan/connectors.md`, and document format rules in `formats.md`, so
  they are only read when needed.
- **Fargate Spot** for the scheduled tasks (see the AWS deploy guide).

## Secrets
Injected as env vars by the platform (Secrets Manager on AWS, Key Vault on Azure); the
run scripts prefer env per-credential, so no vault is contacted. Never commit secrets.

## POC sources (free)
NVD, AlienVault OTX, abuse.ch, a news scraper, and Shodan (perimeter). Splunk is
shared infrastructure — ONE dev instance (Developer License), both clouds' egress IPs
allowlisted — used only by threat-hunting.

## Reporting component (weekly tactical + quarterly strategic)
The reporting engine now runs inside this image as the `reporting` component. In the
original app an Azure OpenAI model (Semantic Kernel) did the analysis and a python-docx
renderer produced the Word file. Here **Claude does the analysis** — it collects and
correlates the intelligence and writes `analysis_result.json` — and the SAME deterministic
renderer (`core/tools/reporting/render_report.py`, vendored stack-neutral, no azure/openai
imports) turns that JSON into the branded GeneLabs `.docx`. `MODE=weekly` (default) builds
the tactical SOC report; `MODE=quarterly` builds the board-level strategic brief. Schema
and grounding gates live in the `genelabs-cti-report` skill.

    COMPONENT=reporting MODE=quarterly ANTHROPIC_MODEL=<bedrock-profile> CLOUD=aws \
      OUTPUT_BUCKET=<bucket> deploy/entrypoint.sh

## Run one component locally
    COMPONENT=bulletin-scan ANTHROPIC_MODEL=<bedrock-profile> CLOUD=aws \
      OUTPUT_BUCKET=<bucket> deploy/entrypoint.sh

## Build once, deploy N times
    docker build -f deploy/Dockerfile -t cti-pipeline:poc .
Then one Fargate task (or Container Apps Job) per component, each with its own
`COMPONENT` and cadence. See deploy/aws and deploy/azure.
