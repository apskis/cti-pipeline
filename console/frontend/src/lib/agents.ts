// Agent role names used across the console, so every page says which agent did what.
// The same names appear on the How it's built tab (lib/showcase.ts); a test keeps them in step.

/** The Coordinator is deploy/entrypoint.sh: plain code that starts each agent in turn. */
export const COORDINATOR = "Coordinator";

// Each component's main session. Builder sessions are the Writer whatever the component.
const COMPONENT_AGENT: Record<string, string> = {
  "bulletin-scan": "Analyst",
  reporting: "Reporter",
  "perimeter-scan": "Watcher",
  "threat-hunting": "Hunter",
  "documentation-sync": "Librarian",
  "program-console": "Scorekeeper",
};

export const WRITER = "Writer";

export const componentAgent = (component: string): string =>
  COMPONENT_AGENT[component] ?? "Agent";

const isBuild = (label: string): boolean => label.startsWith("build");

/** The agent behind one model session, from the label the cost log gives it. */
export const sessionAgent = (component: string, label: string): string =>
  isBuild(label) ? WRITER : componentAgent(component);

/** "Writer, pass 2" for builder sessions, the bare role name otherwise. */
export function sessionName(component: string, label: string): string {
  const pass = /^build-(\d+)$/.exec(label);
  if (pass) return `${WRITER}, pass ${pass[1]}`;
  return sessionAgent(component, label);
}

/** The agents that took part in a run, in the order they first worked. */
export function runAgents(component: string, labels: string[]): string[] {
  return [...new Set(labels.map((l) => sessionAgent(component, l)))];
}

/** "the Analyst and the Writer" */
export function joinAgents(agents: string[]): string {
  const named = agents.map((a) => `the ${a}`);
  if (named.length <= 1) return named.join("");
  return `${named.slice(0, -1).join(", ")} and ${named.at(-1)}`;
}

// Who does each stage of a bulletin scan run, as PipelineFlow shows them.
const STAGE_AGENT: Record<string, string> = {
  feeds: COORDINATOR,
  scan: "Analyst",
  triage: "Analyst",
  build: WRITER,
  check: COORDINATOR,
  deliver: COORDINATOR,
};

export const stageAgent = (key: string): string | null => STAGE_AGENT[key] ?? null;

/** Which agents produced a kind of document, for the report reader. */
export function kindAgents(kind: string): string {
  if (kind === "weekly" || kind === "quarterly") return "Written by the Reporter";
  return "Picked by the Analyst, written by the Writer";
}
