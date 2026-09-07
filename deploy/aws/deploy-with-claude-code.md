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

---

## Step 0 — Preflight
Run and show results; STOP if any fails.
```
aws sts get-caller-identity                 # expect account 574625227402
aws configure get region || echo us-east-1  # target us-east-1
docker info >/dev/null 2>&1 && echo "docker OK" || echo "docker NOT running"
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

## Step 2 — Build and push the image (ECR)
```
aws ecr describe-repositories --repository-names $ECR --region $REGION 2>/dev/null \
  || aws ecr create-repository --repository-name $ECR --region $REGION
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker build -f deploy/Dockerfile -t $ECR:latest .
docker tag $ECR:latest $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$ECR:latest
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$ECR:latest
```
**STOP** — confirm the push succeeded (image digest shown).

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

## Step 7 — ECS cluster + task definition
```
aws ecs create-cluster --cluster-name $CLUSTER --region $REGION 2>/dev/null || true
```
Register a Fargate task def `cti-bulletin-scan` (write JSON to generated/):
- requiresCompatibilities FARGATE, networkMode awsvpc, cpu 1024, memory 2048.
- executionRoleArn = cti-pipeline-exec, taskRoleArn = cti-pipeline-task.
- One container `cti` from `$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$ECR:latest`.
  - `environment`: COMPONENT=bulletin-scan, MODEL_BACKEND=bedrock, CLOUD=aws,
    AWS_REGION=$REGION, ANTHROPIC_MODEL=$MODEL, OUTPUT_BUCKET=$BUCKET, MODE=weekly.
  - `secrets`: NVD_API_KEY→NVD_ARN, SHODAN_API_KEY→SHODAN_ARN, OTX_API_KEY→OTX_ARN.
  - `logConfiguration`: awslogs → group $LOGS, region $REGION, stream-prefix bulletin.
**STOP** — show the task def JSON before registering.

## Step 8 — Networking
Use the default VPC for the POC:
```
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $REGION)
SUBNETS=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC --query "Subnets[].SubnetId" --output text --region $REGION)
```
Create a security group `cti-pipeline-sg` in $VPC with **egress all, no ingress**. Fargate
needs a public subnet + `assignPublicIp=ENABLED` to reach Bedrock and the feeds.

## Step 9 — Test run (one-off) and verify
```
aws ecs run-task --cluster $CLUSTER --launch-type FARGATE \
  --task-definition cti-bulletin-scan --count 1 --region $REGION \
  --network-configuration "awsvpcConfiguration={subnets=[<one public subnet>],securityGroups=[<sg>],assignPublicIp=ENABLED}"
```
Tail logs until the task stops, then confirm output landed:
```
aws logs tail $LOGS --follow --region $REGION      # Ctrl-C when the task exits
aws s3 ls s3://$BUCKET/bulletin-scan/ --region $REGION
```
Read one output object back and show April a summary. **STOP** — do not create the schedule
until the test run has produced a bulletin in S3.

## Step 10 — Schedule (only after a green test run)
Create an EventBridge Scheduler rule `cti-bulletin-scan` on the component's cadence
(`components/bulletin-scan/component.yaml` → `0 13 * * 1-5`), target = ECS run-task with the
task def, cluster, and the same network configuration, plus a scheduler role that may
`ecs:RunTask` and `iam:PassRole` the two task roles. Show the config. **STOP** — confirm.

## Step 11 — Replicate to the other components
Each of perimeter-scan, threat-hunting, reporting, program-console, documentation-sync uses
the SAME image with a different `COMPONENT` (and, for reporting, `MODE=weekly|quarterly`) and
its own cadence from its `component.yaml`. Register one task def per component (or reuse one
family with container env overrides at run-task time) and one schedule each. Do reporting
next; leave threat-hunting until Splunk is up. **STOP** after each.

---

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
