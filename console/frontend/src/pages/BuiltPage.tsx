import clsx from "clsx";
import { ArrowDown, Bot, Cloud, Code2, FileText, Laptop, Server } from "lucide-react";

import { useSummary } from "../api/client";
import StatTile from "../components/StatTile";
import { formatCount, formatMoney } from "../lib/format";
import {
  AGENTS,
  type Agent,
  CLOUD_ROWS,
  FLOW,
  HANDOFFS,
  PRACTICES,
  ROADMAP,
  STACK,
} from "../lib/showcase";

const Section = ({
  title,
  lead,
  children,
}: {
  title: string;
  lead?: string;
  children: React.ReactNode;
}) => (
  <section className="mt-10">
    <h2 className="text-lg font-medium text-brand">{title}</h2>
    {lead && <p className="mt-1 max-w-3xl text-sm text-muted">{lead}</p>}
    <div className="mt-4">{children}</div>
  </section>
);

const STATUS_STYLE: Record<Agent["status"], string> = {
  live: "bg-ok-bg text-ok-ink",
  ready: "bg-accent-soft text-accent-soft-ink",
  waiting: "bg-unknown-bg text-unknown-ink",
};

/** Live numbers from the cost log, so the pitch rests on real output. Hidden until loaded. */
const ByTheNumbers = () => {
  const summary = useSummary();
  if (!summary.data) return null;
  const s = summary.data;
  const documents = Object.values(s.counts).reduce((a, b) => a + b, 0);
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatTile label="Documents produced" value={formatCount(documents)} />
      <StatTile label="CVEs tracked" value={formatCount(s.cves_tracked)} />
      <StatTile label="Run days" value={formatCount(s.run_days)} />
      <StatTile
        label="Model cost so far"
        value={formatMoney(s.total_cost_usd)}
        detail="At API prices"
      />
    </div>
  );
};

const AgentCard = ({ agent }: { agent: Agent }) => (
  <li className="flex h-full flex-col rounded-xl border border-line bg-surface p-4">
    <div className="flex items-start justify-between gap-2">
      <div>
        <p className="text-xs uppercase tracking-wide text-faint">{agent.role}</p>
        <p className="font-medium">The {agent.persona}</p>
        <p className="text-xs text-muted">{agent.name}</p>
      </div>
      <span className={clsx("shrink-0 rounded-full px-2 py-0.5 text-xs", STATUS_STYLE[agent.status])}>
        {agent.statusNote}
      </span>
    </div>
    <p className="mt-3 flex items-center gap-1.5 text-sm font-medium text-accent">
      {agent.model ? <Bot aria-hidden="true" size={16} /> : <Code2 aria-hidden="true" size={16} />}
      {agent.model ?? "No model, plain Python"}
    </p>
    <p className="mt-2 text-sm text-muted">{agent.why}</p>
    <div className="mt-auto pt-3">
      <p className="text-xs text-faint">{agent.cadence}</p>
      <ul className="mt-2 flex flex-wrap gap-1" aria-label={`${agent.name} tools`}>
        {agent.tools.map((tool) => (
          <li key={tool} className="rounded bg-raised px-2 py-0.5 text-xs text-muted">
            {tool}
          </li>
        ))}
      </ul>
    </div>
  </li>
);

const Handoffs = () => (
  <ol className="max-w-3xl">
    {HANDOFFS.map((step, i) => (
      <li key={i}>
        <div
          className={clsx(
            "rounded-xl border p-4",
            step.model ? "border-accent bg-accent-soft" : "border-line bg-surface",
          )}
        >
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-medium">The {step.actor}</span>
            <span className={clsx("text-xs", step.model ? "text-accent" : "text-muted")}>
              {step.model ?? "Plain code"}
            </span>
          </p>
          <p className="mt-1 text-sm text-muted">{step.does}</p>
        </div>
        {step.leaves && (
          <p className="flex items-center gap-2 py-2 pl-4 text-xs text-muted">
            <ArrowDown aria-hidden="true" size={14} className="text-faint" />
            <FileText aria-hidden="true" size={14} className="text-faint" />
            {step.leaves}
          </p>
        )}
      </li>
    ))}
  </ol>
);

const Flow = () => (
  <>
    <p className="mb-3 flex flex-wrap gap-4 text-xs text-muted">
      <span className="flex items-center gap-1.5">
        <span className="inline-block size-3 rounded-sm bg-accent" /> Claude does this step
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block size-3 rounded-sm border border-rung bg-surface" /> Plain
        code, no model call
      </span>
    </p>
    <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {FLOW.map((step, i) => (
        <li
          key={step.title}
          className={clsx(
            "flex flex-col rounded-xl border p-3",
            step.by === "model"
              ? "border-accent bg-accent-soft"
              : "border-line bg-surface",
          )}
        >
          <p className="flex items-baseline gap-2">
            <span className="text-xs text-faint">{i + 1}</span>
            <span className="font-medium">{step.title}</span>
          </p>
          <p
            className={clsx(
              "mt-1 text-xs font-medium",
              step.by === "model" ? "text-accent" : "text-muted",
            )}
          >
            {step.who}
          </p>
          <p className="mt-2 text-sm text-muted">{step.what}</p>
        </li>
      ))}
    </ol>
  </>
);

const CloudTable = () => (
  <div className="overflow-x-auto rounded-xl border border-line bg-surface">
    <table className="w-full min-w-[520px] text-left text-sm">
      <thead className="bg-raised text-muted">
        <tr>
          <th scope="col" className="px-3 py-2 font-medium">
            Need
          </th>
          <th scope="col" className="px-3 py-2 font-medium">
            <span className="flex items-center gap-1.5">
              <Cloud aria-hidden="true" size={15} /> AWS
            </span>
          </th>
          <th scope="col" className="px-3 py-2 font-medium">
            <span className="flex items-center gap-1.5">
              <Server aria-hidden="true" size={15} /> Azure
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        {CLOUD_ROWS.map((row) => (
          <tr key={row.need} className="border-t border-line">
            <th scope="row" className="px-3 py-2 font-medium">
              {row.need}
            </th>
            <td className="px-3 py-2 text-muted">{row.aws}</td>
            <td className="px-3 py-2 text-muted">{row.azure}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const BuiltPage = () => (
  <article>
    <header className="rounded-xl border border-line bg-surface p-6">
      <p className="text-xs uppercase tracking-wide text-faint">How it's built</p>
      <h1 className="mt-1 text-2xl font-medium text-brand">
        An AI pipeline that runs a threat intelligence program
      </h1>
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="text-sm font-medium">The problem</h2>
          <p className="mt-1 text-sm text-muted">
            A small security team has to read dozens of feeds and advisories every day, decide
            what matters to the business, and turn that into bulletins, hunt plans, awareness
            posts and leadership reports. Done by hand, the reading crowds out the analysis.
          </p>
        </div>
        <div>
          <h2 className="text-sm font-medium">The solution</h2>
          <p className="mt-1 text-sm text-muted">
            A set of scheduled Claude agents that collect, judge, write and check, in the
            team's own house style. People review finished, branded documents instead of raw
            feeds. Each step uses the cheapest thing that can do it well, from plain code to Opus.
          </p>
        </div>
      </div>
      <ByTheNumbers />
    </header>

    <Section
      title="The agents"
      lead="Each component is its own scheduled agent with its own task, tools and model. The model is picked for the work, not by default."
    >
      <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {AGENTS.map((agent) => (
          <AgentCard key={agent.name} agent={agent} />
        ))}
      </ul>
    </Section>

    <Section
      title="How the agents work together"
      lead="Agents never call each other. The Coordinator, a plain shell script, starts each one in turn, and every handoff is a file you can open and read. Each agent starts with a clean context and ends when its job is done."
    >
      <Handoffs />
    </Section>

    <Section
      title="How one run flows"
      lead="Three of the nine steps use a model. Everything around them is plain code, which keeps runs cheap, repeatable and easy to debug."
    >
      <Flow />
    </Section>

    <Section title="Design choices" lead="What this build shows about building AI systems that hold up.">
      <ul className="grid gap-3 sm:grid-cols-2">
        {PRACTICES.map((p) => (
          <li key={p.title} className="rounded-xl border border-line bg-surface p-4">
            <p className="font-medium">{p.title}</p>
            <p className="mt-1 text-sm text-muted">{p.body}</p>
          </li>
        ))}
      </ul>
    </Section>

    <Section
      title="Deploying it"
      lead="One container image runs on AWS or Azure. Each cloud has a step by step runbook that Claude Code follows, stopping for approval before anything is created."
    >
      <CloudTable />
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface p-4">
          <p className="flex items-center gap-1.5 font-medium">
            <Laptop aria-hidden="true" size={16} /> Running locally today
          </p>
          <p className="mt-1 text-sm text-muted">
            Docker on a laptop with a Claude plan and Opus. Output stays in a local folder and
            this console reads it. No cloud account is touched.
          </p>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4">
          <p className="flex items-center gap-1.5 font-medium">
            <Cloud aria-hidden="true" size={16} /> The one cloud difference
          </p>
          <p className="mt-1 text-sm text-muted">
            Claude runs on Bedrock, not on Azure. On AWS the task role covers it. On Azure the
            job calls Bedrock across clouds with a narrowly scoped key kept in Key Vault.
          </p>
        </div>
      </div>
    </Section>

    <Section
      title="Roadmap"
      lead="Ideas weighed and kept for later, each with what has to be true before it is worth the cost."
    >
      <ol className="grid gap-3 md:grid-cols-2">
        {ROADMAP.map((item) => (
          <li key={item.title} className="flex flex-col rounded-xl border border-line bg-surface p-4">
            <span className="self-start rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent-soft-ink">
              {item.when}
            </span>
            <p className="mt-2 font-medium">{item.title}</p>
            <p className="mt-1 text-sm text-muted">{item.body}</p>
          </li>
        ))}
      </ol>
    </Section>

    <Section title="Built with">
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {STACK.map(({ group, items }) => (
          <div key={group} className="rounded-xl border border-line bg-surface p-4">
            <dt className="text-xs uppercase tracking-wide text-faint">{group}</dt>
            {items.map((item) => (
              <dd key={item} className="mt-1 text-sm">
                {item}
              </dd>
            ))}
          </div>
        ))}
      </dl>
    </Section>
  </article>
);

export default BuiltPage;
