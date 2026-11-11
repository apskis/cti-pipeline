import type { Audience, Stakeholder, TeamAsk } from "../api/types";

export interface ReportForPerson {
  id: string;
  /** The teams in that report this person answers for, with the questions put to them. */
  teams: TeamAsk[];
}

/** Reports that name one of this person's teams, newest ID first. */
export function reportsFor(person: Stakeholder, audience: Audience | undefined): ReportForPerson[] {
  if (!audience) return [];
  return Object.entries(audience.reports)
    .map(([id, report]) => ({
      id,
      teams: report.teams.filter((t) => t.stakeholders.includes(person.id)),
    }))
    .filter((r) => r.teams.length > 0)
    .sort((a, b) => b.id.localeCompare(a.id, undefined, { numeric: true }));
}

export interface Recipients {
  /** Each team the report names, with the people on file for it (none is a gap). */
  teams: { name: string; questions: string[]; people: Stakeholder[] }[];
  /** People who get every report of this kind, whether or not it names their team. */
  byKind: Stakeholder[];
  /** Everyone above once, in that order. */
  everyone: Stakeholder[];
}

export function recipientsFor(
  reportId: string,
  kind: string,
  audience: Audience | undefined,
  people: Stakeholder[],
): Recipients {
  const byId = new Map(people.map((p) => [p.id, p]));
  const teams = (audience?.reports?.[reportId]?.teams ?? []).map((t) => ({
    name: t.name,
    questions: t.questions,
    people: t.stakeholders.flatMap((id) => byId.get(id) ?? []),
  }));
  const byKind = people.filter((p) => p.receives.includes(kind));
  const everyone = [...new Map([...teams.flatMap((t) => t.people), ...byKind].map((p) => [p.id, p])).values()];
  return { teams, byKind, everyone };
}

/** "Name <email>; Name <email>", ready to paste into a To line. People without email are left out. */
export const distributionList = (people: Stakeholder[]): string =>
  people
    .filter((p) => p.email)
    .map((p) => `${p.name} <${p.email}>`)
    .join("; ");

/** A comma separated field as a tidy list. */
export const splitList = (text: string): string[] =>
  text
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

export const CHANNEL_LABELS = { email: "Email", teams: "Teams", slack: "Slack", other: "Other" } as const;
