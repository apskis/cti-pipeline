# Deploy the CTI pipeline to Azure — Claude Code runbook

Run from the repo root on April's machine:

```
claude "Read deploy/azure/deploy-with-claude-code.md and execute it. Stop at each
STOP marker and wait for my approval before continuing."
```

Same image, same components as the AWS deploy — different target. `CLOUD=azure` ships
output to Blob Storage; compute is a **Container Apps Job** with a cron schedule.

## The one honest constraint (read first)
Claude Code runs the model on **Amazon Bedrock or Google Vertex, not Azure**. So even on
Azure compute the model call goes to **Bedrock cross-cloud**. On AWS the task role supplies
Bedrock credentials automatically; on Azure there is no AWS role, so the job needs an **AWS
IAM user access key scoped to Bedrock**, injected from Key Vault. That access key is a real
secret — April creates the IAM user in AWS and stores its key in Key Vault; you never type
the value. (Alternatively run `MODEL_BACKEND=subscription` with a Max token, but keep a
personal token out of a scheduled cloud job.)

## Guardrails
- Never put a secret value (API keys, the AWS access key) in a file, job env, or commit.
  Secrets live in Key Vault only, entered by April. You reference them.
- Least privilege on every role assignment. Idempotent: check-then-create. Approve at STOPs.
- Write generated ARM/JSON to `deploy/azure/generated/` (gitignored).

## Fixed facts (confirm, do not assume)
- Subscription: **CTI_Automated_Reporting_POC** (`3110f85f-14ad-4094-aa61-98712d65cd9a`).
- Model backend: **bedrock**, model `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, region
  `us-east-1` (the AWS region the cross-cloud call targets).
- First component: **bulletin-scan**.

---

## Step 0 — Preflight
```
az account show                          # confirm the CTI_Automated_Reporting_POC subscription
az account set --subscription 3110f85f-14ad-4094-aa61-98712d65cd9a
az version
```
Confirm April already has (or creates now, in AWS) an IAM user with only
`bedrock:InvokeModel` + `InvokeModelWithResponseStream` on the Sonnet model, and its access
key ready to paste into Key Vault in Step 5. **STOP**.

## Step 1 — Variables
```
SUB=3110f85f-14ad-4094-aa61-98712d65cd9a
RG=cti-pipeline-rg
LOC=eastus
ACR=ctipipeline$RANDOM        # must be globally unique, lowercase
STORAGE=ctipipelineout$RANDOM # globally unique, lowercase
CONTAINER=reports
KV=cti-pipeline-kv-$RANDOM    # globally unique
IDENTITY=cti-pipeline-id
CAENV=cti-pipeline-env
MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
AWSREGION=us-east-1
```

## Step 2 — Resource group
```
az group create -n $RG -l $LOC
```

## Step 3 — Build the image in Azure (ACR) — no local Docker
```
az acr create -g $RG -n $ACR --sku Basic
az acr build -r $ACR -t cti-pipeline:latest -f deploy/Dockerfile .
```
`az acr build` uploads the repo and builds in the cloud. **STOP** — confirm the build.

## Step 4 — Storage (Blob output)
```
az storage account create -g $RG -n $STORAGE -l $LOC --sku Standard_LRS --min-tls-version TLS1_2
az storage container create --account-name $STORAGE -n $CONTAINER --auth-mode login
```

## Step 5 — Key Vault + secrets (April enters values)
```
az keyvault create -g $RG -n $KV -l $LOC --enable-rbac-authorization true
```
Ask April to set each secret in her terminal (paste real values):
```
az keyvault secret set --vault-name $KV -n nvd-api-key       --value "PASTE_NVD"
az keyvault secret set --vault-name $KV -n shodan-api-key    --value "PASTE_SHODAN"
az keyvault secret set --vault-name $KV -n otx-api-key       --value "PASTE_OTX"
az keyvault secret set --vault-name $KV -n aws-access-key-id     --value "PASTE_AWS_KEY_ID"
az keyvault secret set --vault-name $KV -n aws-secret-access-key --value "PASTE_AWS_SECRET"
```
**STOP** — confirm all five exist (`az keyvault secret list --vault-name $KV -o table`).

## Step 6 — Managed identity + role assignments
```
az identity create -g $RG -n $IDENTITY
```
Grant the identity, scoped:
- **AcrPull** on the ACR.
- **Key Vault Secrets User** on the vault.
- **Storage Blob Data Contributor** on the storage account.
Capture the identity's clientId and principalId. **STOP** — show the three role assignments.

## Step 7 — Container Apps environment
```
az extension add -n containerapp --upgrade
az containerapp env create -g $RG -n $CAENV -l $LOC
```

## Step 8 — Container Apps Job (scheduled)
Create a **Schedule**-triggered job for bulletin-scan (cadence from
`components/bulletin-scan/component.yaml` → `0 13 * * 1-5`). Write the create command to
generated/ and show it. Key pieces:
- `--trigger-type Schedule --cron-expression "0 13 * * 1-5"`
- `--image $ACR.azurecr.io/cti-pipeline:latest`, `--registry-server $ACR.azurecr.io`
  with `--registry-identity` = the user-assigned identity.
- `--mi-user-assigned` = the identity (so `az login --identity` works at runtime for Blob).
- Key Vault secret refs (`--secrets`) using `keyvaultref:<secret-uri>,identityref:<id>` for
  nvd/shodan/otx/aws-access-key-id/aws-secret-access-key.
- `--env-vars`: COMPONENT=bulletin-scan MODEL_BACKEND=bedrock CLOUD=azure
  ANTHROPIC_MODEL=$MODEL AWS_REGION=$AWSREGION STORAGE_ACCOUNT=$STORAGE
  OUTPUT_CONTAINER=$CONTAINER MODE=weekly
  NVD_API_KEY=secretref:nvd-api-key SHODAN_API_KEY=secretref:shodan-api-key
  OTX_API_KEY=secretref:otx-api-key
  AWS_ACCESS_KEY_ID=secretref:aws-access-key-id
  AWS_SECRET_ACCESS_KEY=secretref:aws-secret-access-key
**STOP** — show the full job definition before creating.

## Step 9 — Test run and verify
```
az containerapp job start -g $RG -n cti-bulletin-scan
az containerapp job execution list -g $RG -n cti-bulletin-scan -o table
# tail logs:
az containerapp job logs show -g $RG -n cti-bulletin-scan --container cti --follow
# confirm output landed:
az storage blob list --account-name $STORAGE -c $CONTAINER --auth-mode login -o table
```
Read one blob back and summarize for April. The cron schedule is already attached to the
job, so no separate scheduler is needed. **STOP** — confirm a bulletin landed before moving on.

## Step 10 — Replicate to the other components
Same image, one job per component with its own `COMPONENT` (and `MODE` for reporting) and the
cadence from its `component.yaml`. Do reporting next; hold threat-hunting until Splunk is up.
**STOP** after each.

---

## Parity note
This mirrors `deploy/aws/deploy-with-claude-code.md` exactly, service for service:
ECR↔ACR, Fargate task↔Container Apps Job, EventBridge↔the job's cron, Secrets Manager↔Key
Vault, S3↔Blob, task role↔managed identity. The only asymmetry is the Bedrock credential:
AWS provides it by role, Azure needs the IAM user key in Key Vault. That is the multi-cloud
story — one image, `CLOUD` and `MODEL_BACKEND` switch the target.
