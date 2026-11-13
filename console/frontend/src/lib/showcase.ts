// Content for the "How it's built" tab. Static facts about the pipeline's design, kept as
// data so the page stays a layout and a test can check the copy follows the house rules.
// Source of truth: deploy/entrypoint.sh, components/*/component.yaml and the two deploy
// runbooks. Update this file when those change.

export interface Agent {
  /** The role name a demo audience remembers, such as "Analyst". */
  persona: string;
  name: string;
  role: string;
  cadence: string;
  /** The model that does the judgement work, or null where plain code does the job. */
  model: string | null;
  why: string;
  tools: string[];
  status: "live" | "ready" | "waiting";
  statusNote: string;
}

export const AGENTS: Agent[] = [
  {
    persona: "Analyst",
    name: "Bulletin scan",
    role: "Collect",
    cadence: "Mon, Wed, Fri",
    model: "Sonnet 4.5 in the cloud, Opus locally",
    why: "Reads every feed, searches for context, decides what matters to GeneLabs and ranks it. That is research and judgement, so it gets the strongest model.",
    tools: ["News search", "NVD", "Enrichment", "ICS advisories"],
    status: "live",
    statusNote: "Runs locally today",
  },
  {
    persona: "Writer",
    name: "Document builders",
    role: "Write",
    cadence: "After each scan",
    model: "Haiku 4.5",
    why: "Fill branded templates from a scan that already made the decisions. No research needed, so the fastest model does it at a fraction of the price.",
    tools: ["15 GeneLabs skills", "Word, PDF, Excel"],
    status: "live",
    statusNote: "Runs locally today",
  },
  {
    persona: "Reviewer",
    name: "Document review",
    role: "Check",
    cadence: "After each build",
    model: "Sonnet 4.5 in the cloud, Opus locally",
    why: "Reads each new document cold, with none of the Writer's context, and checks every claim against its source and every CVE against NVD. That is judgement, so it gets the strong model. It flags problems and never edits: a person decides.",
    tools: ["NVD", "Web fetch"],
    status: "live",
    statusNote: "Runs locally today",
  },
  {
    persona: "Reporter",
    name: "Reporting",
    role: "Report",
    cadence: "Weekly and quarterly",
    model: "Sonnet 4.5 in the cloud, Opus locally",
    why: "Turns a week or a quarter of findings into analysis for leadership. A plain Python renderer then makes the .docx, so layout never costs a model call.",
    tools: ["News search", "NVD", "Enrichment", "ICS advisories"],
    status: "ready",
    statusNote: "Built, not yet scheduled",
  },
  {
    persona: "Watcher",
    name: "Perimeter scan",
    role: "Watch",
    cadence: "Weekly",
    model: "Sonnet 4.5 in the cloud, Opus locally",
    why: "Looks at what GeneLabs exposes to the internet and judges which exposures need an owner and a fix.",
    tools: ["Shodan", "Enrichment", "NVD"],
    status: "ready",
    statusNote: "Built, not yet scheduled",
  },
  {
    persona: "Hunter",
    name: "Threat hunting",
    role: "Investigate",
    cadence: "Daily",
    model: "Sonnet 4.5 in the cloud, Opus locally",
    why: "Writes hypotheses, runs real Splunk searches and reads the results. The hardest reasoning in the pipeline.",
    tools: ["Splunk", "Enrichment", "AWS API"],
    status: "waiting",
    statusNote: "Waiting on a Splunk instance",
  },
  {
    persona: "Librarian",
    name: "Documentation sync",
    role: "Govern",
    cadence: "Monthly",
    model: "Haiku 4.5",
    why: "Keeps the program documents in line with what the pipeline actually does. Comparing and updating text is light work.",
    tools: ["The repo's document set"],
    status: "waiting",
    statusNote: "Waiting on the plan documents",
  },
  {
    persona: "Scorekeeper",
    name: "Program console",
    role: "Measure",
    cadence: "Daily",
    model: null,
    why: "Refreshing numbers needs no judgement. It runs as plain Python and never starts a model session.",
    tools: ["Its own KPI data"],
    status: "waiting",
    statusNote: "Waiting on its collector",
  },
];

export interface Handoff {
  /** Who acts: the Coordinator is plain code, everyone else is a Claude session. */
  actor: string;
  model: string | null;
  does: string;
  /** The file this step leaves for the next one, or null at the end. */
  leaves: string | null;
}

// One bulletin scan run, as the Coordinator drives it. Agents never call each other:
// each one reads a file, does its work, writes a file and ends.
export const HANDOFFS: Handoff[] = [
  {
    actor: "Coordinator",
    model: null,
    does: "Restores state, prefetches the feeds and starts the Analyst.",
    leaves: "Feed digest",
  },
  {
    actor: "Analyst",
    model: "Sonnet 4.5 or Opus",
    does: "Decides what matters and gives each item a bulletin or hunt ID.",
    leaves: "Dedup log with new IDs",
  },
  {
    actor: "Coordinator",
    model: null,
    does: "Picks the next four pending IDs and starts a fresh Writer.",
    leaves: "Pending list",
  },
  {
    actor: "Writer",
    model: "Haiku 4.5",
    does: "Builds each document on the list in GeneLabs house style. Repeats in a new session until nothing is pending.",
    leaves: "Finished documents",
  },
  {
    actor: "Coordinator",
    model: null,
    does: "Lists the documents this run built and starts a fresh Reviewer.",
    leaves: "Review list",
  },
  {
    actor: "Reviewer",
    model: "Sonnet 4.5 or Opus",
    does: "Checks each document against its sources and NVD and flags what does not hold up. It cannot edit a document.",
    leaves: "One review per document",
  },
  {
    actor: "Coordinator",
    model: null,
    does: "Checks every document, rebuilds the ID counters and ships the output with its reviews.",
    leaves: null,
  },
];

export interface FlowStep {
  title: string;
  /** "model" when Claude does the step, "code" when plain code does. */
  by: "model" | "code";
  who: string;
  what: string;
}

export const FLOW: FlowStep[] = [
  {
    title: "Schedule fires",
    by: "code",
    who: "EventBridge or Container Apps cron",
    what: "Starts one container for one component. The same image serves every component.",
  },
  {
    title: "Restore state",
    by: "code",
    who: "Shell",
    what: "Pulls the last run's registers and dedup log from storage, so only new items get reported.",
  },
  {
    title: "Wire up tools",
    by: "code",
    who: "Python",
    what: "Writes an MCP config with only the servers this component needs. Keys stay in the environment, never in the file.",
  },
  {
    title: "Prefetch feeds",
    by: "code",
    who: "Python",
    what: "Fetches and filters every feed into one digest. Doing this inside the model cost a turn per feed.",
  },
  {
    title: "Scan",
    by: "model",
    who: "Sonnet 4.5 or Opus",
    what: "Reads the digest, searches for context, ranks what matters and assigns bulletin and hunt IDs in the dedup log.",
  },
  {
    title: "Build documents",
    by: "model",
    who: "Haiku 4.5",
    what: "Fresh sessions build four documents at a time. Anything not finished stays pending for the next run, never lost.",
  },
  {
    title: "Review documents",
    by: "model",
    who: "Sonnet 4.5 or Opus",
    what: "A fresh Reviewer checks each new document's claims against its sources and NVD. It flags, never edits, and a failed review never stops a run from shipping.",
  },
  {
    title: "Check and finalize",
    by: "code",
    who: "Python",
    what: "Renders reports, verifies every document and rebuilds the ID counters from what is on disk.",
  },
  {
    title: "Ship and log cost",
    by: "code",
    who: "Shell",
    what: "Copies output to S3 or Blob storage. Every session logs its cost, turns and tokens, which feed this console.",
  },
];

export interface Practice {
  title: string;
  body: string;
}

export const PRACTICES: Practice[] = [
  {
    title: "The right model for each job",
    body: "Research and judgement get Sonnet or Opus. Template filling gets Haiku. Anything with no judgement in it runs as plain code. Model choice is a cost decision made per step.",
  },
  {
    title: "Code where code is enough",
    body: "Feed fetching, rendering, state and verification are deterministic Python. The model is only used where a person would otherwise have to think.",
  },
  {
    title: "Context kept small on purpose",
    body: "One session cannot carry a dozen documents, so the scan only decides and fresh builder sessions write in small batches. A failure delays a document, it never loses one.",
  },
  {
    title: "Guardrails on every run",
    body: "Headless runs load an explicit allow and deny list. Each component sees only its own MCP servers. Secrets arrive from Secrets Manager or Key Vault as environment, never in files or commits.",
  },
  {
    title: "Checks the model cannot skip",
    body: "A Splunk query linter, programmatic checks on every .docx and a sanitization gate for posts that leave the security team. Then a second model, with clean context, checks the facts. The pipeline proves its own output.",
  },
  {
    title: "Cost you can see",
    body: "Every model session writes one line with its cost, turns and tokens. The Runs tab and the cost chart read straight from it.",
  },
  {
    title: "Domain knowledge as skills",
    body: "House style, report formats and hard lessons from real hunts live in 15 GeneLabs skills. The model follows the same playbook an analyst would.",
  },
  {
    title: "One image, any cloud",
    body: "CLOUD picks AWS, Azure or local. MODEL_BACKEND picks Bedrock or a Claude plan. Nothing else changes.",
  },
];

export interface RoadmapItem {
  title: string;
  when: string;
  body: string;
}

// Ideas weighed and kept for later, with what has to be true before each is worth doing.
export const ROADMAP: RoadmapItem[] = [
  {
    title: "Writers in parallel",
    when: "When run time matters",
    body: "The Coordinator would start several Writers at once instead of one batch after another. Runs finish sooner for the same cost. Today a run finishes well inside its window, so speed is not the bottleneck.",
  },
  {
    title: "Helper agents for the Hunter",
    when: "Once Splunk is live",
    body: "The Hunter could hand separate lines of inquiry to helper agents that each run their own searches, then pull the answers together. Worth it when there is real hunt data to search in parallel.",
  },
];

export const STACK: { group: string; items: string[] }[] = [
  { group: "Agents", items: ["Claude Code, headless", "Model Context Protocol", "Agent skills"] },
  { group: "Models", items: ["Claude Opus", "Claude Sonnet 4.5", "Claude Haiku 4.5", "Amazon Bedrock"] },
  { group: "Pipeline", items: ["Python 3.11+", "uv", "python-docx", "Docker"] },
  { group: "Console", items: ["React", "TypeScript", "Vite", "Tailwind", "TanStack Query", "FastAPI"] },
  { group: "Quality", items: ["unittest", "pytest", "Vitest", "ruff", "ESLint"] },
];

export interface CloudRow {
  need: string;
  aws: string;
  azure: string;
}

export const CLOUD_ROWS: CloudRow[] = [
  { need: "Build the image", aws: "CodeBuild into ECR", azure: "az acr build into ACR" },
  { need: "Run a component", aws: "ECS task on Fargate Spot", azure: "Container Apps Job" },
  { need: "Schedule it", aws: "EventBridge Scheduler", azure: "The job's own cron" },
  { need: "Keep secrets", aws: "Secrets Manager", azure: "Key Vault" },
  { need: "Store output and state", aws: "S3", azure: "Blob Storage" },
  { need: "Identity", aws: "Task role", azure: "Managed identity" },
  {
    need: "Call the model",
    aws: "Bedrock, credentials from the task role",
    azure: "Bedrock across clouds, with a scoped AWS key from Key Vault",
  },
];
