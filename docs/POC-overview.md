# CTI Pipeline POC — overview

Sanitized **GeneLabs** build of the CTI automation, reproduced on April's own **AWS and
Azure** with free/open sources. One container image, seven components, switchable cloud and
model backend. This file is the context and plan; the **executable source of truth** is the
two deploy runbooks:

- `deploy/aws/deploy-with-claude-code.md`
- `deploy/azure/deploy-with-claude-code.md`

Run either from the repo root with Claude Code. No Docker: AWS builds via **CodeBuild**,
Azure via **`az acr build`**.

## Model backend
- **Cloud** → Bedrock + **Sonnet 4.5** (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`).
  Opus is not available on this Bedrock account (tier gated). Auth: AWS task role; on Azure,
  an AWS IAM user key in Key Vault (cross-cloud, because Claude Code runs the model on
  Bedrock/Vertex, not Azure).
- **Local** → Max plan + **Opus** via `MODEL_BACKEND=subscription` and a
  `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`.

## Free API keys
| Secret | Get it from | Cost | Used by |
|---|---|---|---|
| `NVD_API_KEY` | nvd.nist.gov/developers/request-an-api-key | free | bulletin, reporting, CVE |
| `OTX_API_KEY` | otx.alienvault.com → settings | free | enrichment / feeds |
| `ABUSECH_AUTH_KEY` | auth.abuse.ch | free | enrichment / feeds |
| `SHODAN_API_KEY` | already held | yours | perimeter scan |

Values go into Secrets Manager (AWS) or Key Vault (Azure), entered by April. Never commit.

## Components and cadence
| Component | Cadence | Sources (POC) |
|---|---|---|
| bulletin-scan (Collect) | weekdays | open feeds, news scraper, NVD |
| perimeter-scan (Watch) | weekly | Shodan |
| reporting (Report) | weekly + quarterly | the above, aggregated (Claude does the analysis) |
| program-console (Measure) | hourly | its own KPI data |
| documentation-sync (Govern) | monthly | the repo's doc set |
| threat-hunting (Investigate) | daily | Splunk (BOTS data) — **deferred until Splunk is up** |

## Splunk (gates threat-hunting only)
- ONE shared instance, **Developer License** (10 GB/day, keeps token auth — the Free license
  disables auth and breaks the MCP). Dev license was under review.
- EC2 t3.large, security group locked to April's IP on 8000/8089/22, both clouds' egress IPs
  allowlisted on 8089.
- Fill with **BOTS (Boss of the SOC)** datasets (github.com/splunk/botsv3) for synthetic hunt
  data. Map real index→sourcetype pairs into the `genelabs-splunk-spl` skill.
- `SPLUNK_URL=https://<ip>:8089`, `SPLUNK_TOKEN=<token>`. Add to Secrets Manager / Key Vault,
  then create the threat-hunting task def/job (its deferred step in each runbook).

## Order of operations
1. Get the three free keys (NVD, OTX, abuse.ch); Shodan already held.
2. Run the deploy runbook for the target cloud — it builds the image and stands up every
   component except threat-hunting, smoke-testing bulletin-scan first.
3. Stand up Splunk + BOTS in parallel (the long pole); add threat-hunting when it is live.
4. Repeat the other cloud from its runbook for the multi-cloud demonstration.

> The earlier `POC_Step1_AWS_Commands.md` (local Docker build/push) is superseded by
> `deploy/aws/deploy-with-claude-code.md` and is intentionally not kept here.
