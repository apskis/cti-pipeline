# Deploy the CTI pipeline to AWS — Claude Code runbook

Run this from the repo root on April's machine:

```
claude "Read deploy/aws/deploy-with-claude-code.md and execute it. Stop at each
STOP marker and wait for my approval before continuing."
```

You (Claude Code) are provisioning April's **personal** AWS account. Go step by step,
show the command before running anything that creates or changes a resource, and pause
at every **STOP**. This is a POC: prefer simple, least privilege, and idempotent.

## Guardrails (read first)
- **Never put a secret value in any file, task definition, env block, or commit.** API
  keys go into Secrets Manager only, entered by April in her own terminal. You reference
  them by ARN.
- **Least privilege.** Scope every IAM policy to the exact bucket, secrets, and model.
- **Idempotent.** Before creating anything, check if it exists (describe/list) and reuse it.
- **Approve destructive steps.** Show the command, wait for "yes" at each STOP.
- Write intermediate JSON (policies, task def) to `deploy/aws/generated/` and add that
  folder to `.gitignore`. Never commit generated files that could contain ARNs of secrets.
- Adapt shell syntax to the OS you are on (PowerShell or bash). AWS CLI commands are the same.

## Fixed facts (confirm, do not assume)
- Account: `574625227402`  •  Region: `us-east-1`
- Model backend: **bedrock**, model = `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
  (Opus is not available on this account; Sonnet 4.5 is confirmed invokable.)
- Image: built from `deploy/Dockerfile` at repo root. Entry `deploy/entrypoint.sh`
  selects the component by `COMPONENT` and the backend by `MODEL_BACKEND`.
- First component to prove the plumbing: **bulletin-scan** (needs open feeds, NVD, no Splunk).
- **No local Docker.** The image is built in AWS by CodeBuild (Step 2), the same way
  Azure uses `az acr build`. April installs nothing.

---

## Step 0 — Preflight
Run and show results; STOP if any fails.
```
aws sts get-caller-identity                 # expect account 574625227402
aws configure get region || echo us-east-1  # target us-east-1
```
Confirm Sonnet 4.5 invokes:
```
aws bedrock-runtime converse --region us-east-1 \
  --model-id us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --messages '[{"role":"user","content":[{"text":"say ok"}]}]' \
  --inference-config '{"maxTokens":5}'
```
**STOP** — report preflight before continuing.

## Step 1 — Variables
Set these in your shell (adapt to PowerShell if needed):
```
ACCOUNT=574625227402
REGION=us-east-1
MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
ECR=cti-pipeline
BUCKET=cti-pipeline-out-$ACCOUNT
CLUSTER=cti-pipeline
LOGS=/ecs/cti-pipeline
```

## Step 2 — Build and push the image with CodeBuild (no local Docker)
Build in AWS from the local source. You (Claude Code) do all of this; April installs nothing.

1. **ECR repo** (idempotent):
```
aws ecr describe-repositories --repository-names $ECR --region $REGION 2>/dev/null \
  || aws ecr create-repository --repository-name $ECR --region $REGION
```
2. **Build bucket + upload source.** Create a private bucket and upload a zip of the working
   tree, EXCLUDING `.git`, `out/`, `__pycache__`, `deploy/*/generated/`, `.venv`:
```
BUILDBUCKET=cti-pipeline-build-$ACCOUNT
aws s3api create-bucket --bucket $BUILDBUCKET --region $REGION
aws s3api put-public-access-block --bucket $BUILDBUCKET \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
# zip with your shell (PowerShell: Compress-Archive; bash: git archive or zip -r),
# then:
aws s3 cp cti-pipeline-src.zip s3://$BUILDBUCKET/source.zip
```
3. **CodeBuild service role** `cti-pipeline-build` (trust `codebuild.amazonaws.com`), scoped to:
   ECR auth + push to the `$ECR` repo, read `s3://$BUILDBUCKET/*`, and CloudWatch Logs.
   Write the policy JSON to `generated/`. **STOP** — show it before creating.
4. **CodeBuild project** `cti-pipeline-build`:
   - source: `S3` = `$BUILDBUCKET/source.zip`
   - environment: `aws/codebuild/standard:7.0`, LINUX_CONTAINER, `BUILD_GENERAL1_SMALL`,
     **privilegedMode = true** (needed to run `docker build`; the CodeBuild image already has Docker).
   - env vars: ACCOUNT, REGION, ECR.
   - inline buildspec:
     - pre_build: `aws ecr get-login-password | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com`
     - build: `docker build -f deploy/Dockerfile -t $ECR:latest .`
     - post_build: tag + `docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$ECR:latest`
5. **Run it and wait:**
```
aws codebuild start-build --project-name cti-pipeline-build --region $REGION
# poll: aws codebuild batch-get-builds --ids <id> --query "builds[0].buildStatus"
```
**STOP** — confirm `SUCCEEDED` and that `aws ecr describe-images --repository-name $ECR`
shows the `latest` tag.

## Step 3 — Output bucket (S3)
Create private, versioned:
```
aws s3api create-bucket --bucket $BUCKET --region $REGION
aws s3api put-public-access-block --bucket $BUCKET \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled
```

## Step 4 — Secrets (April enters values)
**Do not type the key values yourself. Ask April to run these in her terminal**, one per
key, pasting her real value in place of PASTE_*:
```
aws secretsmanager create-secret --name cti/nvd-api-key    --secret-string "PASTE_NVD"    --region $REGION
aws secretsmanager create-secret --name cti/shodan-api-key --secret-string "PASTE_SHODAN" --region $REGION
aws secretsmanager create-secret --name cti/otx-api-key    --secret-string "PASTE_OTX"    --region $REGION
```
Then capture the ARNs (safe to read; not secret):
```
aws secretsmanager list-secrets --region $REGION \
  --query "SecretList[?starts_with(Name,'cti/')].[Name,ARN]" --output table
```
Save the three ARNs as NVD_ARN, SHODAN_ARN, OTX_ARN. **STOP** — confirm all three exist.

## Step 5 — IAM roles
Create two roles trusted by `ecs-tasks.amazonaws.com`. Write the JSON to
`deploy/aws/generated/` and apply.

**Execution role** `cti-pipeline-exec` — pull image, read the three secrets, write logs:
- Attach managed `service-role/AmazonECSTaskExecutionRolePolicy`.
- Inline `secrets-read` allowing `secretsmanager:GetSecretValue` on `NVD_ARN`,
  `SHODAN_ARN`, `OTX_ARN` only.

**Task role** `cti-pipeline-task` — what the container itself may call:
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` on Resources:
  - `arn:aws:bedrock:$REGION:$ACCOUNT:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0`
  - `arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0`
    (the `us.` profile is cross-region; it needs the foundation-model ARN in the routed regions).
- `s3:PutObject` on `arn:aws:s3:::$BUCKET/*`.
Show both policy documents. **STOP** — confirm before creating.

## Step 6 — Log group
```
aws logs create-log-group --log-group-name $LOGS --region $REGION 2>/dev/null || true
aws logs put-retention-policy --log-group-name $LOGS --retention-in-days 30 --region $REGION
```

## Step 7 — ECS cluster + one task definition per component
```
aws ecs create-cluster --cluster-name $CLUSTER --region $REGION 2>/dev/null || true
```
Register one Fargate task def per component. All share: FARGATE, awsvpc, cpu 1024, memory
2048, executionRoleArn=`cti-pipeline-exec`, taskRoleArn=`cti-pipeline-task`, one container
`cti` from the ECR image, `logConfiguration` → `$LOGS` (stream-prefix = the component), and
common env: COMPONENT / MODEL_BACKEND=bedrock / CLOUD=aws / AWS_REGION=$REGION /
ANTHROPIC_MODEL=$MODEL / OUTPUT_BUCKET=$BUCKET / MODE=weekly. Per component:

| task def | COMPONENT | secrets (Secrets Manager) |
|---|---|---|
| cti-bulletin-scan      | bulletin-scan      | NVD, OTX |
| cti-perimeter-scan     | perimeter-scan     | SHODAN, NVD, OTX |
| cti-reporting          | reporting          | NVD, OTX |
| cti-program-console    | program-console    | (none) |
| cti-documentation-sync | documentation-sync | (none) |

MODE only affects reporting; keep it `weekly` on the task def and override to `quarterly` on
the quarterly schedule (Step 10). program-console and documentation-sync take no external
keys but still run the model, so they rely on the task role for Bedrock. threat-hunting is
deferred (Step 11). Write each task def JSON to `generated/` and register with
`aws ecs register-task-definition`. **STOP** — show `cti-bulletin-scan` first; once approved,
register the other four the same way.

## Step 8 — Networking
Use the default VPC for the POC:
```
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $REGION)
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC --query "Subnets[].SubnetId" --output text --region $REGION)
```
Create a security group `cti-pipeline-sg` in $VPC with **egress all, no ingress**. Fargate
needs a public subnet + `assignPublicIp=ENABLED` to reach Bedrock and the feeds.

## Step 9 — Smoke test (bulletin-scan) and verify
Prove the plumbing with one on-demand run before wiring schedules:
```
aws ecs run-task --cluster $CLUSTER --launch-type FARGATE \
  --task-definition cti-bulletin-scan --count 1 --region $REGION \
  --network-configuration "awsvpcConfiguration={subnets=[<one public subnet>],securityGroups=[<sg>],assignPublicIp=ENABLED}"
aws logs tail $LOGS --follow --region $REGION      # Ctrl-C when the task exits
aws s3 ls s3://$BUCKET/bulletin-scan/ --region $REGION
```
Read one output object back and summarize for April. **STOP** — only wire schedules after a
green run produced a bulletin in S3.

## Step 10 — Schedules for every component (EventBridge Scheduler)
Create a schedule group `cti-pipeline`, a scheduler role (`ecs:RunTask` + `iam:PassRole` on
the two task roles), then one schedule per row (FlexibleTimeWindow OFF), target = ECS RunTask
with the task def, cluster, and the Step 8 network config. Cadences come from each
`component.yaml`:

| schedule | task def | cron (UTC) | override |
|---|---|---|---|
| bulletin-scan       | cti-bulletin-scan      | `0 13 * * 1-5`      | — |
| perimeter-scan      | cti-perimeter-scan     | `0 13 * * 1`        | — |
| reporting-weekly    | cti-reporting          | `0 13 * * 1`        | — |
| reporting-quarterly | cti-reporting          | `0 13 1 1,4,7,10 *` | containerOverrides MODE=quarterly |
| program-console     | cti-program-console    | `0 * * * *`         | — |
| documentation-sync  | cti-documentation-sync | `0 6 1 * *`         | — |

For `reporting-quarterly`, set the target's `containerOverrides` to
`environment:[{name:MODE,value:quarterly}]`.
**Scheduler role trust policy:** condition it on `aws:SourceAccount` only. Scheduler
pre-validates that it can assume the role during `CreateSchedule`, before the schedule
ARN exists, so an `ArnLike` on `aws:SourceArn` fails every create with "The execution
role you provide must allow AWS EventBridge Scheduler to assume the role". Note EventBridge Scheduler cron is 6-field with a
year and uses `?` for an unspecified day — translate each 5-field cron accordingly (e.g.
`0 13 * * 1-5` → `cron(0 13 ? * MON-FRI *)`). **STOP** — list the six schedules when done.

## Step 11 — threat-hunting (deferred until Splunk)
threat-hunting needs a live Splunk (dev license pending). When it is up: store `SPLUNK_URL`
and `SPLUNK_TOKEN` in Secrets Manager, register `cti-threat-hunting` (COMPONENT=threat-hunting,
secrets SPLUNK_URL/SPLUNK_TOKEN + NVD/OTX), grant the exec role read on those secrets, and add
a schedule at `0 14 * * *`. Do not create it now — its task would fail with no Splunk endpoint.

## Running locally on the Max plan (Opus)
To run any component on your own machine against your Max plan instead of Bedrock:
```
claude setup-token                     # one-time; approve in browser, copy the token
export CLAUDE_CODE_OAUTH_TOKEN=<token>  # PowerShell: $env:CLAUDE_CODE_OAUTH_TOKEN="<token>"
export MODEL_BACKEND=subscription
export ANTHROPIC_MODEL=opus
export COMPONENT=bulletin-scan OUTPUT_DIR=./out CLOUD=aws OUTPUT_BUCKET=$BUCKET
bash deploy/entrypoint.sh
```
Verify Opus actually served (the Max token has a known tier-detection bug):
```
claude -p --model opus "say ok"        # must not reply that it switched to Sonnet
```
Keep the personal token out of the cloud task definitions — local and on-demand only.
