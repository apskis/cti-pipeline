import { useCompanies, useMe } from "../api/client";

/**
 * What the person may do with the company shown. The backend decides and refuses
 * anything else; this only keeps the page from offering buttons that would be refused.
 */
export function useAccess() {
  const { data: me } = useMe();
  const { data: companies } = useCompanies();
  const shown = companies?.active ?? "";
  return {
    me,
    signedIn: me?.auth === "oidc",
    canWrite: !!me && shown !== "" && (me.platform_admin || me.roles[shown] === "admin"),
    canManage: !!me?.can_manage,
  };
}
