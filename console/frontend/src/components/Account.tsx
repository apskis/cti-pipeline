import { LogIn, LogOut, UserRound } from "lucide-react";

import { SIGN_IN_URL, useSignOut } from "../api/client";
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
