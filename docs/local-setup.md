# Run the pipeline locally

Runs any component on your own machine, in the same container image the cloud uses, on
your Claude Max (or Pro) plan. Nothing is billed per token and no cloud account is
needed after the one-time state copy in step 4.

How it differs from the cloud run:

| Piece   | Cloud (AWS)                 | Local                              |
|---------|-----------------------------|------------------------------------|
| Trigger | EventBridge Scheduler cron  | You run a script (or your own cron) |
| Compute | Fargate Spot task           | Docker on your machine             |
| Model   | Bedrock, billed per token   | Your Claude plan                   |
| State   | `s3://<bucket>/<component>/`| `out/<component>/`                 |
| Keys    | Secrets Manager             | `.env` file (gitignored)           |
| Switch  | `CLOUD=aws`                 | `CLOUD=local`                      |

## 1. Install the prerequisites

- **Docker Desktop** (Windows or macOS) or Docker Engine (Linux). Check: `docker version`.
- **Claude Code CLI**, only to mint the token: `npm install -g @anthropic-ai/claude-code`.
- **AWS CLI**, only for the one-time state copy in step 4. Skip it for a fresh start.
- This repo, cloned and up to date: `git pull`.

## 2. Get a Claude plan token

```
claude setup-token
```

Approve in the browser and copy the token it prints. It is tied to your account, so
treat it like a password: it goes only in `.env`, which git ignores and the Docker build
excludes (`.dockerignore`).

## 3. Create your `.env`

```
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
```

Fill in `CLAUDE_CODE_OAUTH_TOKEN` and whichever feed keys you have (NVD, OTX, Shodan are
free). An empty key just skips that source; the run says so in its output.
`ANTHROPIC_MODEL=opus` uses Opus on Max; set `sonnet` if you hit plan limits.

## 4. Copy the cloud state (once, optional)

The cloud keeps each component's dedup log, registers, next IDs and past deliverables in
S3. Copy them down so the first local run reports only what is new, instead of treating
everything as new:

```
scripts/pull-cloud-state.sh           # PowerShell: .\scripts\pull-cloud-state.ps1
```

No AWS CLI? Unzip a state export (a zip whose top folder is `out/`) in the repo root
instead; the result is the same `out/<component>/` layout.

This only reads from S3. Do it **after** the last cloud run you care about and **before**
pausing the schedules, so nothing is lost in between.

## 5. Run a component

```
scripts/run-local.sh bulletin-scan          # PowerShell: .\scripts\run-local.ps1 bulletin-scan
```

The first run builds the image (a few minutes). Later runs reuse it; add `--build`
(PowerShell `-Build`) after a `git pull`. Other components:

| Component            | Cloud cadence      | Notes                                  |
|----------------------|--------------------|----------------------------------------|
| `bulletin-scan`      | Mon, Wed, Fri      | Needs NVD and OTX keys for best output |
| `perimeter-scan`     | Monday             | Needs the Shodan key                   |
| `reporting`          | Monday + quarterly | `MODE=quarterly` for the quarterly brief |
| `documentation-sync` | 1st of the month   |                                        |

## 6. Check the result

- The log ends with a `[cost]` line per Claude session. On your plan the dollar figure is
  what the run *would* cost at API prices, not a charge.
- Deliverables land in `out/<component>/` (bulletins, registers, reports). The scan
  report is `out/bulletin-scan/reports/scan-YYYY-MM-DD.md`.
- `out/<component>/state/cost-log.jsonl` keeps the history of every run.

## 7. Then pause the cloud

Once a local run of each component you need has worked, pause the five schedules in the
`cti-pipeline` EventBridge Scheduler group (AWS console, or ask Claude). Pausing keeps
everything deployed for a later restart and stops all model spend; the idle setup costs a
few dollars a month for secrets and image storage. See `docs/aws-setup-guide.md` to bring
it back.

## Optional: run it on a schedule locally

The machine has to be on at the run time.

- **macOS / Linux** (`crontab -e`), Mon/Wed/Fri 09:00:
  `0 9 * * 1,3,5 cd /path/to/cti-pipeline && scripts/run-local.sh bulletin-scan >> logs/bulletin.log 2>&1`
- **Windows**: Task Scheduler, action `powershell.exe`, arguments
  `-File C:\path\to\cti-pipeline\scripts\run-local.ps1 bulletin-scan`.

Keep in mind that a Max plan has rolling usage limits shared with your own interactive
use, and it is a personal subscription: fine for running your own work on demand, not a
substitute for an organisation's API or Bedrock account on a real deployment.

## Windows notes

- **Docker Desktop** needs WSL 2; the installer offers to enable it. Start Docker Desktop
  before running anything (the whale icon must say "running").
- **Claude Code** for the token: `irm https://claude.ai/install.ps1 | iex` in PowerShell,
  or `npm install -g @anthropic-ai/claude-code` if you already have Node.js.
- **Script blocked** ("running scripts is disabled on this system"): run once
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry.
- **Line endings** are handled for you: `.gitattributes` keeps shell scripts LF, the
  Dockerfile strips stray CRs, and `run-local.ps1` removes the CRs Notepad adds to `.env`.
- **Unzipping the state export**: right click, Extract All, and pick the repo folder so
  you get `cti-pipeline\out\bulletin-scan\...`, not `out\out\...`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `set CLAUDE_CODE_OAUTH_TOKEN` | `.env` is missing the token, or has quotes around it |
| Says it switched Opus to Sonnet | Known Max token tier bug; set `ANTHROPIC_MODEL=sonnet` or re-run `claude setup-token` |
| Everything reported as new | Step 4 was skipped; run `pull-cloud-state` and re-run |
| `unknown CLOUD=` | Old image; rebuild with `--build` |
