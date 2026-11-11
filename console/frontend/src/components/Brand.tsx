import clsx from "clsx";
import { Monitor, Moon, Sun } from "lucide-react";

import symbolUrl from "../assets/genelabs-symbol.png";
import { type ThemeChoice, useTheme } from "../lib/theme";

/**
 * The GeneLabs DNA helix, taken from the brand kit's official logo. Its dark strand would
 * vanish on the charcoal page, so in dark mode it sits on a small Mist tile.
 */
export const BrandSymbol = ({ className }: { className?: string }) => (
  <span className={clsx("inline-flex shrink-0 items-center justify-center rounded-md bg-symbol-tile p-0.5", className)}>
    <img src={symbolUrl} alt="" aria-hidden className="h-full w-auto" />
  </span>
);

/** Symbol, divider and wordmark kept together as one lockup, as the brand guide asks. */
export const BrandLockup = () => (
  <div className="flex items-center gap-3">
    <BrandSymbol className="h-11" />
    <span aria-hidden className="h-9 w-px bg-rung" />
    <div className="leading-tight">
      <h1 className="text-xl font-semibold tracking-tight text-brand">GeneLabs</h1>
      <p className="text-[0.7rem] font-medium tracking-[0.12em] text-accent uppercase">
        Cyber Threat Intelligence
      </p>
    </div>
  </div>
);

const CHOICES: { value: ThemeChoice; label: string; Icon: typeof Sun }[] = [
  { value: "system", label: "System", Icon: Monitor },
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
];

/** System, light or dark. Remembered in this browser. */
export const ThemeSwitch = () => {
  const { choice, choose } = useTheme();
  return (
    <div role="group" aria-label="Theme" className="inline-flex rounded-md border border-line bg-surface p-0.5">
      {CHOICES.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          aria-pressed={choice === value}
          title={`${label} theme`}
          onClick={() => choose(value)}
          className={clsx(
            "inline-flex items-center gap-1 rounded px-2 py-1 text-xs",
            choice === value ? "bg-accent-soft font-medium text-accent-soft-ink" : "text-muted hover:text-ink",
          )}
        >
          <Icon aria-hidden size={14} />
          <span className="sr-only sm:not-sr-only">{label}</span>
        </button>
      ))}
    </div>
  );
};
