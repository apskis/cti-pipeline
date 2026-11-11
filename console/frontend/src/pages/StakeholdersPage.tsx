import clsx from "clsx";
import { ArrowLeft, Pencil, Plus, Trash2, UserRound } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { useAudience, useDeliverables, useStakeholderWrites, useStakeholders } from "../api/client";
import type { Audience, Channel, Stakeholder, StakeholderInput } from "../api/types";
import LoadState from "../components/LoadState";
import { KIND_LABELS, kindLabel } from "../lib/kinds";
import { newStakeholderHref, reportHref, stakeholderHref } from "../lib/route";
import { CHANNEL_LABELS, reportsFor, splitList } from "../lib/stakeholders";

const fieldClass = "w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
const buttonClass =
  "inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised disabled:opacity-50";
const primaryClass =
  "inline-flex items-center gap-1.5 rounded-md bg-ink px-3 py-1.5 text-sm text-surface hover:opacity-90 disabled:opacity-50";

const EDIT = "/edit";
const SHOWN_REPORTS = 25;

const EMPTY: StakeholderInput = {
  name: "",
  role: "",
  team: "",
  also_known_as: [],
  email: "",
  channel: "email",
  receives: [],
  interests: [],
  notes: "",
};

/** The route's ID: a stakeholder, the add form ("new"), or the add form for a team. */
function parseSelection(selected: string | null): { id: string | null; newTeam: string | null } {
  if (selected === null) return { id: null, newTeam: null };
  if (selected === "new") return { id: null, newTeam: "" };
  if (selected.startsWith("new:")) return { id: null, newTeam: selected.slice(4) };
  return { id: selected, newTeam: null };
}

const Chips = ({ items, empty }: { items: string[]; empty: string }) =>
  items.length === 0 ? (
    <span className="text-muted">{empty}</span>
  ) : (
    <span className="flex flex-wrap gap-1">
      {items.map((item) => (
        <span key={item} className="rounded bg-raised px-1.5 py-0.5 text-xs">
          {item}
        </span>
      ))}
    </span>
  );

interface FormProps {
  id: string | null;
  initial: StakeholderInput;
  kinds: string[];
}

/** Add or change one stakeholder. Saved to config/stakeholders.json on this machine. */
const StakeholderForm = ({ id, initial, kinds }: FormProps) => {
  const { save } = useStakeholderWrites();
  const [form, setForm] = useState(() => ({
    ...initial,
    also_known_as: initial.also_known_as.join(", "),
    interests: initial.interests.join(", "),
  }));
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }));
  const toggleKind = (kind: string) =>
    set(
      "receives",
      form.receives.includes(kind) ? form.receives.filter((k) => k !== kind) : [...form.receives, kind],
    );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const input: StakeholderInput = {
      ...form,
      also_known_as: splitList(form.also_known_as),
      interests: splitList(form.interests),
    };
    save.mutate(
      { id, input },
      { onSuccess: (saved) => (window.location.hash = stakeholderHref(saved.id)) },
    );
  };

  const field = (key: "name" | "role" | "team" | "email", label: string, required = false) => (
    <label className="block text-sm">
      <span className="text-muted">
        {label}
        {required && " (required)"}
      </span>
      <input
        type={key === "email" ? "email" : "text"}
        required={required}
        value={form[key]}
        onChange={(e) => set(key, e.target.value)}
        className={clsx(fieldClass, "mt-1")}
      />
    </label>
  );

  return (
    <form onSubmit={submit} aria-labelledby="form-title" className="flex flex-col gap-4">
      <h2 id="form-title" className="text-lg font-medium">
        {id === null ? "Add a stakeholder" : `Edit ${initial.name}`}
      </h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {field("name", "Name", true)}
        {field("role", "Role")}
        {field("team", "Team", true)}
        {field("email", "Email")}
      </div>
      <label className="block text-sm">
        <span className="text-muted">Also known as, comma separated</span>
        <input
          type="text"
          value={form.also_known_as}
          onChange={(e) => set("also_known_as", e.target.value)}
          placeholder="Security Operations, Detection"
          className={clsx(fieldClass, "mt-1")}
        />
        <span className="mt-1 block text-xs text-faint">
          Other names the reports use for this team. A report that names any of them is matched to
          this person.
        </span>
      </label>
      <fieldset className="text-sm">
        <legend className="text-muted">Gets all</legend>
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {kinds.map((kind) => (
            <label key={kind} className="inline-flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={form.receives.includes(kind)}
                onChange={() => toggleKind(kind)}
              />
              {kindLabel(kind)}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="text-muted">Preferred channel</span>
          <select
            value={form.channel}
            onChange={(e) => set("channel", e.target.value as Channel)}
            className={clsx(fieldClass, "mt-1")}
          >
            {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="text-muted">Interests, comma separated</span>
          <input
            type="text"
            value={form.interests}
            onChange={(e) => set("interests", e.target.value)}
            placeholder="patching, lab instruments"
            className={clsx(fieldClass, "mt-1")}
          />
        </label>
      </div>
      <label className="block text-sm">
        <span className="text-muted">Notes</span>
        <textarea
          value={form.notes}
          onChange={(e) => set("notes", e.target.value)}
          rows={3}
          maxLength={1000}
          className={clsx(fieldClass, "mt-1")}
        />
      </label>
      {save.error && (
        <p role="alert" className="text-sm text-fail-ink">
          Not saved. {save.error.message}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={save.isPending} className={primaryClass}>
          {save.isPending ? "Saving" : "Save"}
        </button>
        <a href={stakeholderHref(id)} className={buttonClass}>
          Cancel
        </a>
      </div>
    </form>
  );
};

const StakeholderDetail = ({ person, audience }: { person: Stakeholder; audience?: Audience }) => {
  const { remove } = useStakeholderWrites();
  const [confirming, setConfirming] = useState(false);
  const reports = useMemo(() => reportsFor(person, audience), [person, audience]);

  return (
    <article aria-labelledby="person-title">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div>
          <p className="text-xs text-muted">{person.team}</p>
          <h2 id="person-title" className="mt-1 text-lg font-medium">
            {person.name}
          </h2>
          {person.role && <p className="text-sm text-muted">{person.role}</p>}
        </div>
        <div className="flex gap-2">
          <a href={stakeholderHref(`${person.id}${EDIT}`)} className={buttonClass}>
            <Pencil aria-hidden size={16} />
            Edit
          </a>
          <button type="button" onClick={() => setConfirming(true)} className={buttonClass}>
            <Trash2 aria-hidden size={16} />
            Delete
          </button>
        </div>
      </header>

      {confirming && (
        <div role="alertdialog" aria-label="Confirm delete" className="mt-4 rounded-md border border-line bg-fail-bg p-3 text-sm">
          <p className="text-fail-ink">
            Delete {person.name} from the list? The previous list is kept as
            config/stakeholders.json.bak until the next save.
          </p>
          {remove.error && <p className="mt-1 text-fail-ink">Not deleted. {remove.error.message}</p>}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(person.id, {
                  onSuccess: () => (window.location.hash = stakeholderHref(null)),
                })
              }
              className={primaryClass}
            >
              Delete
            </button>
            <button type="button" onClick={() => setConfirming(false)} className={buttonClass}>
              Keep
            </button>
          </div>
        </div>
      )}

      <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
        <dt className="text-muted">Email</dt>
        <dd>{person.email ? <a href={`mailto:${person.email}`} className="underline">{person.email}</a> : <span className="text-muted">None on file</span>}</dd>
        <dt className="text-muted">Preferred channel</dt>
        <dd>{CHANNEL_LABELS[person.channel]}</dd>
        <dt className="text-muted">Gets all</dt>
        <dd>
          <Chips items={person.receives.map(kindLabel)} empty="Only reports that name the team" />
        </dd>
        <dt className="text-muted">Also known as</dt>
        <dd>
          <Chips items={person.also_known_as} empty="No other names" />
        </dd>
        <dt className="text-muted">Interests</dt>
        <dd>
          <Chips items={person.interests} empty="None noted" />
        </dd>
        {person.notes && (
          <>
            <dt className="text-muted">Notes</dt>
            <dd className="whitespace-pre-line">{person.notes}</dd>
          </>
        )}
      </dl>

      <section aria-labelledby="named-in" className="mt-6">
        <h3 id="named-in" className="font-medium">
          Reports that ask {person.team} something ({reports.length})
        </h3>
        {reports.length > SHOWN_REPORTS && (
          <p className="mt-1 text-xs text-muted">Showing the {SHOWN_REPORTS} newest.</p>
        )}
        {reports.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No report names this team yet.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-3">
            {reports.slice(0, SHOWN_REPORTS).map((r) => (
              <li key={r.id} className="rounded-md border border-line p-3 text-sm">
                <a href={reportHref(r.id)} className="font-medium underline">
                  {r.id}
                </a>
                {r.teams.map((t) => (
                  <div key={t.name} className="mt-1">
                    {t.name !== person.team && <p className="text-xs text-muted">As {t.name}</p>}
                    <ul className="ml-4 list-disc">
                      {t.questions.map((q) => (
                        <li key={q}>{q}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
};

/** Teams the reports ask questions of that nobody on the list covers. */
const Gaps = ({ audience }: { audience?: Audience }) => {
  const gaps = audience?.unmatched ?? [];
  if (gaps.length === 0) return null;
  return (
    <section aria-labelledby="gaps-title" className="mt-6 rounded-xl border border-line bg-surface p-3">
      <h2 id="gaps-title" className="text-sm font-medium">
        Named in reports, nobody on file ({gaps.length})
      </h2>
      <p className="mt-1 text-xs text-muted">
        Add a stakeholder, or add the name to someone&apos;s &quot;also known as&quot;.
      </p>
      <ul className="mt-2 max-h-64 overflow-y-auto text-sm">
        {gaps.map((g) => (
          <li key={g.team} className="flex items-center justify-between gap-2 py-1">
            <span className="min-w-0 truncate" title={g.reports.join(", ")}>
              {g.team} <span className="text-xs text-muted">· {g.reports.length}</span>
            </span>
            <a href={newStakeholderHref(g.team)} className="shrink-0 text-xs underline">
              Add
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
};

const NoList = ({ hasExample }: { hasExample: boolean }) => {
  const { startFromExample } = useStakeholderWrites();
  return (
    <div className="mx-auto max-w-lg rounded-xl border border-line bg-surface p-6 text-center">
      <UserRound aria-hidden className="mx-auto text-muted" />
      <p className="mt-2 font-medium">No stakeholder list yet.</p>
      <p className="mt-1 text-sm text-muted">
        The list says who each report is for. It is saved in config/stakeholders.json on this
        machine and never committed.
      </p>
      {startFromExample.error && (
        <p role="alert" className="mt-2 text-sm text-fail-ink">
          {startFromExample.error.message}
        </p>
      )}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {hasExample && (
          <button
            type="button"
            disabled={startFromExample.isPending}
            onClick={() => startFromExample.mutate()}
            className={primaryClass}
          >
            Start from the example list
          </button>
        )}
        <a href={newStakeholderHref()} className={buttonClass}>
          <Plus aria-hidden size={16} />
          Add the first stakeholder
        </a>
      </div>
    </div>
  );
};

const StakeholdersPage = ({ selected }: { selected: string | null }) => {
  const list = useStakeholders();
  const audience = useAudience();
  const deliverables = useDeliverables();
  const [query, setQuery] = useState("");

  const people = list.data?.stakeholders;
  const kinds = useMemo(() => {
    const present = new Set((deliverables.data ?? []).map((d) => d.kind));
    return [...new Set([...Object.keys(KIND_LABELS), ...present])];
  }, [deliverables.data]);
  const groups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const shown = (people ?? []).filter((p) =>
      `${p.name} ${p.team} ${p.role} ${p.also_known_as.join(" ")}`.toLowerCase().includes(needle),
    );
    const byTeam = new Map<string, Stakeholder[]>();
    for (const p of [...shown].sort((a, b) => a.name.localeCompare(b.name))) {
      byTeam.set(p.team, [...(byTeam.get(p.team) ?? []), p]);
    }
    return [...byTeam.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [people, query]);

  if (!list.data || !people) {
    return <LoadState error={list.error} onRetry={() => void list.refetch()} />;
  }

  // "sh-1234abcd/edit" is the edit form. A team name after "new:" may itself hold a slash.
  const wantsEdit = selected !== null && !selected.startsWith("new") && selected.endsWith(EDIT);
  const { id, newTeam } = parseSelection(wantsEdit ? selected.slice(0, -EDIT.length) : selected);
  const person = id ? people.find((p) => p.id === id) : undefined;
  const editing = wantsEdit && person !== undefined;
  const open = newTeam !== null || id !== null;

  if (!list.data.exists && newTeam === null) return <NoList hasExample={list.data.has_example} />;

  let panel;
  if (newTeam !== null) {
    panel = <StakeholderForm key={`new:${newTeam}`} id={null} initial={{ ...EMPTY, team: newTeam }} kinds={kinds} />;
  } else if (editing) {
    panel = <StakeholderForm key={`edit:${person.id}`} id={person.id} initial={person} kinds={kinds} />;
  } else if (person) {
    panel = <StakeholderDetail person={person} audience={audience.data} />;
  } else if (id) {
    panel = <p className="py-16 text-center text-muted">No stakeholder {id} on the list.</p>;
  } else {
    panel = (
      <p className="py-16 text-center text-muted">
        Pick someone to see what they get and what the reports ask of their team.
      </p>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-[20rem_minmax(0,1fr)]">
      <div className={clsx(open && "hidden md:block")}>
        <section aria-label="Stakeholders">
          <div className="flex gap-2">
            <label className="sr-only" htmlFor="stakeholder-search">
              Search stakeholders
            </label>
            <input
              id="stakeholder-search"
              type="search"
              placeholder="Search by name or team"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={fieldClass}
            />
            <a href={newStakeholderHref()} className={clsx(buttonClass, "shrink-0")}>
              <Plus aria-hidden size={16} />
              Add
            </a>
          </div>
          <p className="mt-2 text-xs text-muted" aria-live="polite">
            {people.length} {people.length === 1 ? "stakeholder" : "stakeholders"} in{" "}
            {new Set(people.map((p) => p.team)).size} teams
          </p>
          <div className="mt-2 max-h-[60vh] overflow-y-auto rounded-xl border border-line bg-surface">
            {groups.map(([team, members]) => (
              <div key={team} className="border-b border-line last:border-b-0">
                <h2 className="px-3 pt-2 text-xs font-medium text-muted">{team}</h2>
                <ul>
                  {members.map((p) => (
                    <li key={p.id}>
                      <a
                        href={stakeholderHref(p.id)}
                        aria-current={p.id === id ? "page" : undefined}
                        className={clsx("block px-3 py-1.5 text-sm hover:bg-raised", p.id === id && "bg-raised")}
                      >
                        {p.name}
                        {p.role && <span className="block text-xs text-muted">{p.role}</span>}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {groups.length === 0 && (
              <p className="px-3 py-6 text-center text-sm text-muted">
                {people.length === 0 ? "The list is empty." : "Nobody matches."}
              </p>
            )}
          </div>
        </section>
        <Gaps audience={audience.data} />
      </div>

      <section
        aria-label="Stakeholder"
        className={clsx("min-w-0 rounded-xl border border-line bg-surface p-4 md:p-6", !open && "hidden md:block")}
      >
        {open && (
          <a href={stakeholderHref(null)} className="mb-3 inline-flex items-center gap-1 text-sm text-muted md:hidden">
            <ArrowLeft aria-hidden size={16} />
            All stakeholders
          </a>
        )}
        {panel}
      </section>
    </div>
  );
};

export default StakeholdersPage;
