import { Eye, LogIn, LogOut, UserRound } from "lucide-react";

import { SIGN_IN_URL, useCompanies, useSignOut, useViewAs } from "../api/client";
import type { ViewAs } from "../api/types";
import { useAccess } from "../lib/access";

const buttonClass =
  "inline-flex items-center gap-1.5 rounded-md border border-line px-2 py-1 text-xs hover:bg-raised disabled:opacity-50";

/** Shown instead of the console while nobody is signed in. */
export const SignIn = () => (
  <div className="mx-auto mt-16 max-w-md rounded-xl border border-line bg-surface p-6 text-center">
    <UserRound aria-hidden className="mx-auto text-muted" />
    <h1 className="mt-2 text-lg font-medium">Sign in to the CTI console</h1>
    <p className="mt-1 text-sm text-muted">
      Use your work account. What you see depends on the companies your account is in.
    </p>
    <a
      href={SIGN_IN_URL}
      className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-accent-hover"
    >
      <LogIn aria-hidden size={16} />
      Sign in
    </a>
  </div>
);

/** Shown to someone signed in whose account is in no company yet. */
export const NoCompany = () => (
  <div role="note" className="mx-auto mt-8 max-w-md rounded-xl border border-line bg-surface p-6 text-center">
    <p className="font-medium">Your account has no company yet.</p>
    <p className="mt-1 text-sm text-muted">Ask a platform admin to add you to one, then sign in again.</p>
  </div>
);

/** The signed in person and a way out. Nothing under the local, single user console. */
export const Account = () => {
  const { me, signedIn, canWrite } = useAccess();
  const signOut = useSignOut();
  if (!me || !signedIn) return null;
  const role = me.platform_admin ? "Platform admin" : canWrite ? "Company admin" : "Viewer";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-muted" title={me.email || undefined}>
        {me.name} <span className="text-faint">· {role}</span>
      </span>
      <button type="button" className={buttonClass} disabled={signOut.isPending} onClick={() => signOut.mutate()}>
        <LogOut aria-hidden size={14} />
        Sign out
      </button>
    </div>
  );
};

/** Said where someone may look but not change. */
export const ReadOnlyNote = ({ what }: { what: string }) => (
  <p role="note" className="mb-4 rounded-md border border-line bg-raised px-3 py-2 text-sm text-muted">
    You can view {what} but not change it. Changes need a company admin.
  </p>
);

const ROLE_NAMES = { admin: "Company admin", viewer: "Viewer" } as const;

/** "platform", or role and company joined, as a select's value. */
const viewKey = (view: ViewAs): string => (view.role === "platform" ? "platform" : `${view.role}:${view.company}`);

function viewFromKey(key: string): ViewAs {
  const [role, company] = key.split(":");
  return role === "admin" || role === "viewer" ? { role, company: company ?? "" } : { role: "platform", company: null };
}

/**
 * Act as a company admin or viewer, to show each role in a demo without accounts. Only on
 * the local console: under sign in a role comes from each person's account.
 */
export const ViewAsSwitch = () => {
  const { me } = useAccess();
  const { data: companies } = useCompanies();
  const viewAs = useViewAs();
  if (!me?.view_as || !companies) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <label className="inline-flex items-center gap-1.5">
        <Eye aria-hidden size={14} className="text-muted" />
        <span className="text-muted">View as</span>
        <select
          value={viewKey(me.view_as)}
          disabled={viewAs.isPending}
          onChange={(e) => viewAs.mutate(viewFromKey(e.target.value))}
          className="rounded-md border border-line bg-surface px-2 py-1 text-xs text-ink"
        >
          <option value="platform">Platform admin</option>
          {companies.companies.flatMap((c) =>
            (["admin", "viewer"] as const).map((role) => (
              <option key={`${role}:${c.slug}`} value={`${role}:${c.slug}`}>
                {ROLE_NAMES[role]} of {c.name}
              </option>
            )),
          )}
        </select>
      </label>
      {viewAs.isError && (
        <span role="alert" className="text-fail-ink">
          Not switched. {viewAs.error.message}
        </span>
      )}
    </div>
  );
};

/** While acting as another role, says so and offers the way back. */
export const ViewAsBanner = () => {
  const { me } = useAccess();
  const { data: companies } = useCompanies();
  const viewAs = useViewAs();
  const view = me?.view_as;
  if (!view || view.role === "platform") return null;
  const company = companies?.companies.find((c) => c.slug === view.company)?.name ?? view.company;
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-accent bg-raised px-3 py-2 text-sm"
    >
      <span>
        Viewing as <strong>{ROLE_NAMES[view.role]}</strong> of <strong>{company}</strong>. The console acts
        exactly as that role would, refusals included.
      </span>
      <button
        type="button"
        className={buttonClass}
        disabled={viewAs.isPending}
        onClick={() => viewAs.mutate({ role: "platform", company: null })}
      >
        Back to platform admin
      </button>
    </div>
  );
};
