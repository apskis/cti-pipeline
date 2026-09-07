# Task: CTI Program Dashboard refresh

**You almost certainly do not need this file.** The dashboard refresh is pure
Python, so run `bin/refresh-console.sh` and you are done. This file exists for
the case where you want an agent to run the refresh *and* comment on what
moved, e.g. `bin/run-skill.sh --file tasks/cti-program-dashboard-refresh.md`.

It is the ported version of the desktop scheduled task's prompt. Two things
changed in the port and both are marked below.

---

Refresh the GeneLabs CTI Program Dashboard from the files on this machine. Be
quiet: no questions, no task list, no commentary beyond the one line at the end.

Everything needed is in this repo and in the two CTI folders named in `.env`.
Do NOT rewrite, regenerate or "improve" any of the scripts in `dashboard/`, and
do NOT invent, estimate or carry forward numbers. The only source of truth is
what the collector reads off disk this run.

**Step 1, rebuild.** Run exactly this:

    bash bin/refresh-console.sh

It recollects the KPIs from the CTI Deliverables and CTI Documentation folders,
rebuilds the page, and prints two lines: COLLECTED with a timestamp, and
CHANGED with what moved since the previous run.

If the script fails because a CTI folder is missing or unreadable, STOP THERE.
Do not touch the built page. The existing console keeps its last good data and
its stamp simply ages, which is the intended behaviour. Reply with one line
saying which folder was unreachable, and end the run.

If the script itself errors, do not patch it. Reply with the error text and end
the run.

**Step 2, CHANGED IN THE PORT.** The desktop task published the built page
over a hosted claude.ai artifact URL. That step no longer exists and cannot be
reproduced from outside the Claude apps: there is no public API for writing to
an artifact URL. `refresh-console.sh` instead leaves the page at

    <CTI_DOCUMENTATION>/_dashboard/cti_program_dashboard.html

and prints its `file://` path. Bookmark that path. Nothing to do here.

**Step 3, reply with a single line:** the COLLECTED timestamp followed by the
CHANGED summary. If nothing moved, say so in those words. Nothing else.

---

## Cadence note, carried over from the desktop task

The run is daily at 17:05, not hourly. The CTI daily scan runs at 07:02 and the
Falcon hunt at 16:03; 17:05 is the first moment both have finished, so a single
daily rebuild captures the whole working day's output. An earlier run would
produce a console that omits the day's hunts.

This matters for how you word the closing line. On a daily cadence a skipped
run means the console is a DAY old, not an hour old. Say that plainly rather
than letting a reader assume the stamp is nearly fresh.
