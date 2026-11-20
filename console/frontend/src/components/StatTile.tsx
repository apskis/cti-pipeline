import clsx from "clsx";
import type { LucideIcon } from "lucide-react";

interface StatTileProps {
  label: string;
  value: string;
  detail?: string;
  Icon?: LucideIcon;
  /** Draws the tile in the accent, for the one number the page leads with. */
  highlight?: boolean;
}

const StatTile = ({ label, value, detail, Icon, highlight = false }: StatTileProps) => (
  <div
    className={clsx(
      "rounded-xl border p-4",
      highlight ? "border-accent/50 bg-accent-soft" : "border-line bg-surface",
    )}
  >
    <div className="flex items-start justify-between gap-2">
      <p className="text-sm text-muted">{label}</p>
      {Icon && (
        <span className="inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-raised text-accent">
          <Icon aria-hidden size={16} />
        </span>
      )}
    </div>
    <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
    {detail && <p className="mt-1 text-xs text-faint">{detail}</p>}
  </div>
);

export default StatTile;
