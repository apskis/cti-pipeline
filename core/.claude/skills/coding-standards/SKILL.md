---
name: coding-standards
description: "April's cross-project coding standards, bundled from her Cursor rulebooks. Use when writing, refactoring, reviewing, or scaffolding code in ANY of her projects — pick the rule files that match the stack and follow them. Always apply universal.md and security.md; add the language and framework packs for the project at hand (python, javascript, react, api, chrome-extension, azure), plus architecture, scalable-architecture, ux, and versioning where relevant. Triggers on: write code, add a feature, refactor, code review, project structure, new module or component, API design, security review, release and versioning."
---

# Coding standards

These are April's house coding standards, bundled from her Cursor rulebooks. They are
**guidelines, not hard requirements** — apply what fits the stack and the task, and skip
sections that do not apply (for example, ignore Docker or Next.js rules on a project that
uses neither).

## How to use

Read the rule files under `rules/` that match what you are working on. Do not load all of
them every time — load the two defaults plus the packs for the current stack.

**Always:**

- `rules/universal.md` — cross-language standards: structure, naming, DRY/KISS, error
  handling, testing, git, dependencies.
- `rules/security.md` — secrets, input validation, auth, database, API, dependency and
  cloud security. Applies to every project.

**Add by stack (from April's own mapping):**

| Project type | Also read |
|---|---|
| Python / data science | `rules/python.md` |
| Vanilla JS / TS | `rules/javascript.md` |
| Node.js API | `rules/javascript.md`, `rules/api.md` |
| React / Next.js | `rules/javascript.md`, `rules/react.md`, `rules/ux.md` |
| Chrome extension | `rules/javascript.md`, `rules/react.md`, `rules/chrome-extension.md`, `rules/security.md` |
| Azure Functions / Container Apps | `rules/azure.md` |

**Add by concern (any stack):**

- `rules/architecture.md` — project organization, modular design, layering, anti-patterns.
- `rules/scalable-architecture.md` — deployment and cost patterns (serverless, managed DB,
  object storage, queues, multi-tenant, feature gating).
- `rules/ux.md` — Tailwind + shadcn/ui UX patterns, spacing, color tokens, states,
  accessibility (front-end work).
- `rules/versioning.md` — SemVer, changelog, git tagging, commit conventions (releases).

## For this repo (cti-pipeline)

This monorepo is Python plus the Claude Code agent runtime, so the relevant packs are
`universal.md`, `python.md`, and `security.md`. The other packs are here so the standards
travel with the repo and cover April's front-end and extension projects when this skill is
reused there.
