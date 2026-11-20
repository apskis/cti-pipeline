import clsx from "clsx";
import {
  Bug,
  FileText,
  History,
  LayoutDashboard,
  type LucideIcon,
  Network,
  Settings,
  Users,
} from "lucide-react";

import type { Route } from "../lib/route";
import { BrandLockup } from "./Brand";
import { CompanyPicker } from "./CompanyPicker";

type Page = Route["page"];

interface NavItem {
  page: Page;
  label: string;
  href: string;
  Icon: LucideIcon;
}

export const NAV: NavItem[] = [
  { page: "overview", label: "Overview", href: "#/", Icon: LayoutDashboard },
  { page: "reports", label: "Reports", href: "#/reports", Icon: FileText },
  { page: "runs", label: "Runs", href: "#/runs", Icon: History },
  { page: "cves", label: "CVEs", href: "#/cves", Icon: Bug },
  { page: "stakeholders", label: "Stakeholders", href: "#/stakeholders", Icon: Users },
  { page: "built", label: "How it's built", href: "#/built", Icon: Network },
  { page: "settings", label: "Settings", href: "#/settings/branding", Icon: Settings },
];

/** The page's name for the top bar, from the same list the sidebar draws. */
export const pageLabel = (page: Page): string => NAV.find((n) => n.page === page)?.label ?? "Overview";

/**
 * Brand, page links and the company picker. A column down the left on wide screens; on a
 * phone it folds to a header with the links in one scrolling row, so nothing is hidden
 * behind a menu button.
 */
const Sidebar = ({ current }: { current: Page }) => (
  <aside className="flex flex-col border-b border-line bg-surface md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0 md:border-r md:border-b-0">
    <div className="border-b border-line px-4 py-4 md:px-5 md:py-5">
      <BrandLockup />
    </div>
    <nav aria-label="Pages" className="flex gap-1 overflow-x-auto px-2 py-2 [scrollbar-width:none] md:flex-col md:px-3 md:py-4">
      {NAV.map(({ page, label, href, Icon }) => (
        <a
          key={page}
          href={href}
          aria-current={current === page ? "page" : undefined}
          className={clsx(
            "inline-flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm",
            current === page
              ? "bg-accent-soft font-medium text-accent-soft-ink"
              : "text-muted hover:bg-raised hover:text-ink",
          )}
        >
          <Icon aria-hidden size={16} className={current === page ? "text-accent" : undefined} />
          {label}
        </a>
      ))}
    </nav>
    <div className="border-t border-line px-4 py-3 md:mt-auto md:px-5 md:py-4">
      <CompanyPicker stacked />
    </div>
  </aside>
);

export default Sidebar;
