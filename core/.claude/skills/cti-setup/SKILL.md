---
name: cti-setup
description: "Set up the GeneLabs CTI workbench on this machine, including the Amazon Bedrock connection. Installs dependencies, finds the real CTI Deliverables and CTI Documentation folders on this computer, writes cti.config.json, runs the preflight, proves the toolchain works on a scratch document, and optionally registers the monthly schedule. Use on a fresh clone, when the preflight reports failures, when the folders have moved, or when the person asks for help setting this up."
---

# Set up the CTI workbench

You are setting this repository up on April Parker's machine. She is at the
keyboard: ask when you need a decision, and never guess at a folder path when
you can look for it.

Work through the phases in order. Report what you did at the end of each phase
in two or three lines, not a transcript.

## Phase 0: which engine is running

Say which engine you are, because it changes where skills are read from and
which CLI the scheduled runs will use.

| | Claude Code | Cursor |
| --- | --- | --- |
| Skills folder | `.claude/skills/` | `.cursor/skills/` |
| Headless CLI | `claude` | `cursor-agent` |
| Install | `npm install -g @anthropic-ai/claude-code` | comes with the Cursor editor |
| Reaches Bedrock | **yes** | no, chat models only |

`.cursor/skills/` is canonical; `.claude/skills/` mirrors it. Confirm they match:

```
python scripts/sync_skills.py --check
```

If it reports drift, run `python scripts/sync_skills.py` to mirror.

## Phase 1: dependencies

Check the Python version and install the requirements.

```
python --version
python -m venv .venv                                    # if .venv is absent
.venv\Scripts\python -m pip install -r requirements.txt  # Windows
.venv/bin/python -m pip install -r requirements.txt      # macOS, Linux, WSL
```

If `python` is missing or older than 3.10, stop and tell her which version is
installed and what to install. Do not try to install Python yourself.

## Phase 1b: Bedrock

This build sends model calls to Claude models in GeneLabs's AWS account. Only
Claude Code carries that configuration into the tool loop; Cursor's agent does
not, because Cursor limits custom keys to chat models. If she is running you
from Cursor's agent, say so now and point her at Claude Code in the integrated
terminal before going further.

First establish which credential she actually has, because "a Claude API key for
Bedrock" means three different things:

| What she has | Looks like | Variable |
| --- | --- | --- |
| Bedrock API key | a long bearer token from the AWS console | `AWS_BEARER_TOKEN_BEDROCK` |
| IAM access key pair | `AKIA...` plus a secret | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| SSO or named profile | a profile name in `~/.aws/config` | `AWS_PROFILE` |

A key starting `sk-ant-` is **not** Bedrock. That is direct Anthropic API
access, and it needs `ANTHROPIC_API_KEY` with `CLAUDE_CODE_USE_BEDROCK` left
unset. Tell her if that is what she has, rather than trying to make it work.

Ask her which one she has. Never ask her to paste the secret to you; have her
put it in the file herself.

```
cp config/bedrock.env.example config/bedrock.env
```

Help her fill in the region and the pinned model, then verify:

```
python scripts/bedrock_doctor.py            # config and account, no calls
python scripts/bedrock_doctor.py --invoke   # one real, token-billed call
```

Do not proceed to Phase 5 until `--invoke` succeeds. A configuration that looks
right and fails at call time wastes a whole run.

Two things to raise with her here, whether or not she asks:

- **Pin the model.** An unpinned alias resolves to an Opus class default that
  may not be enabled in the account and is billed at the Opus rate. Confirm
  `ANTHROPIC_MODEL` is set and that the preflight found it invocable.
  `docs/MODELS.md` lists what the task actually needs: a vision capable driver,
  **Opus by default**, plus Haiku for background work. April's standing
  preference is to start with Opus; drop to Sonnet only when no Opus is enabled
  in the account, and say so in the run summary when you do. Vision is not
  optional here, because Step 3b renders the document and looks at it.
- **WebSearch does not work on Bedrock.** The doc sync does not need it. The
  bulletin, CVE brief and awareness skills do. Say this plainly rather than
  letting her discover it mid-bulletin.

The alternative to the env file is Claude Code's own wizard, which writes
`~/.claude/settings.json` and pins models after checking what the account can
invoke: run `claude`, choose 3rd-party platform, then Amazon Bedrock. Offer it;
it is the better path for a permanent single user install.

## Phase 2: find the real folders

This is the step most likely to need actual searching. The example config holds
the path as it was on the old machine:

```
C:/Users/<user>/GeneLabs LLC/Security Operations Center - CTI/CTI Deliverables
```

OneDrive tenant folder names vary by machine and by account. Do not assume the
example is right. Look for the folders:

```powershell
# Windows
Get-ChildItem "$env:USERPROFILE" -Directory | Where-Object Name -like "*GeneLabs*"
Get-ChildItem "$env:USERPROFILE" -Directory -Recurse -Depth 3 -ErrorAction SilentlyContinue |
    Where-Object Name -in "CTI Deliverables","CTI Documentation" |
    Select-Object FullName
```

```bash
# macOS, Linux, WSL
find "$HOME" -maxdepth 5 -type d \( -name "CTI Deliverables" -o -name "CTI Documentation" \) 2>/dev/null
```

Then confirm what you found is really the right tree before you write it down.
The deliverables folder should contain `cti-bulletin-log.md` and a
`CTI Threat Hunts` folder. The documentation folder should contain
`Strategy_and_Plan`.

If the search finds nothing, ask her where the folders are rather than guessing.
If OneDrive shows them as online only placeholders, say so: the sync needs the
files locally available, and she may need to mark the folder "Always keep on
this device".

Write both paths into `cti.config.json`, copying from
`cti.config.example.json` first if it does not exist. Use forward slashes even
on Windows so nothing needs escaping. Leave every other key alone.

## Phase 3: preflight

```
python scripts/doctor.py
```

Read the output and act on it. Every FAIL must be resolved before a real run;
report each WARN with what it means rather than silently accepting it. Two
warnings are expected on a fresh install and are not blockers:

- **Claude Code CLI or Cursor CLI not on PATH** — only needed for scheduled and
  headless runs. At least one is required for those; a FAIL on "Headless engine"
  means neither is installed. Offer the install command; do not run it without
  asking.
- **Notification webhook not configured** — explain that without it a run summary
  reaches her only as a desktop toast and a file on disk, and ask whether she
  wants to set `CTI_NOTIFY_WEBHOOK` to a Teams or Slack incoming webhook.

A missing state record is a FAIL worth pausing on. `portfolio_state.md` is the
comparison baseline for every sync. If it is gone, say so plainly and do not let
the first sync invent one from file timestamps.

## Phase 4: prove the toolchain

Do not test on her real documents. Build a scratch document, restyle it, render
it, and look at the result.

```
python .cursor/skills/genelabs-cti-documentation/scripts/build_cti_doc.py <spec> /tmp/probe.docx
python .cursor/skills/genelabs-cti-documentation/scripts/restyle_cti_doc.py /tmp/probe.docx /tmp/probe_styled.docx \
    --doc-id "CTI-TEST-01" --marking "CTI Program Documentation"
python scripts/render_pdf.py /tmp/probe_styled.docx
```

Open the PDF and check four things: the Enterprise Information Security banner
sits clear of the first body element, headings are GeneLabs orange, the footer
carries the wordmark with DOC # and page fields, and there is **no TLP marking**.
Internal program documentation carries no TLP. If one appears, the restyler is
not the patched copy from this repository.

Delete the scratch files when you are done.

## Phase 5: dry run

```powershell
.\scripts\run_doc_sync.ps1 -Force -DryRun     # Windows
./scripts/run_doc_sync.sh --force --dry-run   # elsewhere
```

`-Force` skips the date guard so this can run on any day. `-DryRun` analyses and
reports without writing anything.

This needs an agent CLI, either `claude` or `cursor-agent`. The runner
auto-detects and prefers `claude`; `-Engine cursor` forces the other. If neither
is installed, say so and offer the alternative: she can get the same result by
typing `/cti-doc-sync` in the Agent chat and adding "dry run, analyse and report
only, change nothing".

Read the dry run output with her. Confirm it found the deliverables tree, read
the state record, and reached conclusions that match what she knows about the
portfolio. Do not move to scheduling until she is satisfied with what it found.

Flag the context: the September 2026 scheduled run could not reach the machine
and changed nothing, so the first real run has roughly a month of unreconciled
drift to absorb rather than a normal cycle's worth.

## Phase 6: schedule, only if she wants it

Ask before registering anything.

```powershell
.\scripts\register_schedule.ps1 -At "07:30"    # elevated PowerShell
./scripts/register_schedule.sh --at 07:30      # cron
```

This fires on the 1st, 2nd and 3rd of each month and the date guard does the
work on the first weekday only, matching the Claude task exactly. Tell her the
tradeoff: unlike the cloud task, this needs the machine signed in and awake near
the scheduled time. `-StartWhenAvailable` catches a missed run at the next
opportunity, but a laptop closed for a week will miss the window.

## Finish

Close with a short status: what is configured, what is still warning, whether
the schedule is registered, and the one or two things she should check herself.
Name anything you had to guess at.
