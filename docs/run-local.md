# Running the pipeline on your own machine

The POC path. No cloud, no container, no per token bill: the model runs on the Claude
subscription already signed in to your CLI, so a run costs nothing beyond the plan you
already pay for.

The AWS and Azure runbooks under `deploy/` stay as the enterprise deployment story. This
file is how you demonstrate that the pipeline works.

## One time setup

1. **Claude Code, signed in.**

   ```
   claude login
   claude --version
   ```

2. **Python 3.11 or newer, with the document builders.**

   ```
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r deploy/requirements.txt
   ```

3. **API keys as environment variables.** All three are free. The pipeline reads them
   from the environment, so nothing is written to disk.

   | Variable | Get it from | Used by |
   |---|---|---|
   | `NVD_API_KEY` | nvd.nist.gov/developers/request-an-api-key | bulletin-scan, reporting, perimeter-scan |
   | `OTX_API_KEY` | otx.alienvault.com, under settings | enrichment for the above |
   | `SHODAN_API_KEY` | account.shodan.io | perimeter-scan only |

   ```
   export NVD_API_KEY=...
   export OTX_API_KEY=...
   export SHODAN_API_KEY=...
   ```

   A missing key is not fatal: the run warns and that MCP server returns nothing.

   > These were held in AWS Secrets Manager and were deleted with the rest of the AWS
   > teardown, so the stored copies are gone. Fetch them again from the three sites above.

## Running it

```
./scripts/run_local.sh                      # bulletin-scan, the deepest component
./scripts/run_local.sh perimeter-scan
./scripts/run_local.sh documentation-sync
MODE=quarterly ./scripts/run_local.sh reporting
```

Output lands in `out/` by default, shared by every component. Point it anywhere:

```
OUTPUT_DIR=~/OneDrive/CTI ./scripts/run_local.sh
```

**One shared folder is deliberate, and differs from the cloud layout.** On AWS each
component had its own bucket prefix and therefore its own diverging dedup log, register
and ID counter. Sharing one folder is what the dedup and next ID logic actually wants,
and only `bulletin-scan` writes documents, so there is no contention.

## What a run does

1. Resolves every path in `config/paths.json` under `OUTPUT_DIR` and creates the folders,
   so a bad path fails immediately rather than when a finished document is saved.
2. Generates `.mcp.json` for that component's `enabled_servers`.
3. **Scan pass**: researches the feeds and assigns IDs in `state/dedup-log.md`. It writes
   no documents.
4. **Builder passes** (`bulletin-scan` only): each pass is a fresh context that turns a
   small batch of those IDs into `.docx` files, until nothing is pending. The driver
   rejects a hollow document and queues it again, so a run that reports success has
   actually produced real content.
5. Recomputes `state/next-ids.md` and `state/deliverables-index.md` from the files on
   disk, so the next run dedups correctly even if the model forgot to update its log.

Expect roughly 3 builder passes and tens of minutes for a `bulletin-scan` run.

## Scheduling it

Only if you want it unattended. A POC demo does not need this.

**macOS or Linux**, weekdays at 08:00 local:

```
crontab -e
0 8 * * 1-5 cd /path/to/cti-pipeline && ./scripts/run_local.sh bulletin-scan >> logs/local.log 2>&1
```

Cron gets a minimal environment, so export the keys inside the command or source a file
holding them. `logs/` is gitignored.

**Windows**: Task Scheduler running `bash -lc "cd /path/to/cti-pipeline && ./scripts/run_local.sh"`
under Git Bash or WSL. The scripts are bash; PowerShell is not supported.

An unattended machine with no interactive login needs a token instead:
`CLAUDE_CODE_OAUTH_TOKEN=$(claude setup-token)`.

## Known limits of the POC

- **`threat-hunting` cannot run.** It needs Splunk with BOTS data, plus `SPLUNK_URL` and
  `SPLUNK_TOKEN`. This was deferred in the original plan and still is.
- **The `search` MCP server has no implementation.** It is listed in `enabled_servers` for
  `bulletin-scan` and `reporting`, and the run prints `skipped=['search']`. Those
  components fall back to WebFetch.
- **`reporting` exits 4 if the model did not write `analysis_result.json`.** That is the
  guard working: the deterministic renderer will not invent a report.
- **Branded .docx templates are not in the repo**, so documents build in a plain fallback
  style. Every run says so once.
