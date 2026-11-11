import clsx from "clsx";
import { Monitor, Moon, Sun } from "lucide-react";

import { type ThemeChoice, useTheme } from "../lib/theme";

/**
 * The GeneLabs DNA symbol from the brand kit. The strands and rungs take theme colours,
 * so the mark stays legible on the light Mist page and on the dark Forest page.
 */
export const BrandSymbol = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 76 112" aria-hidden className={className}>
    <path
      d="M24 22 L51 22 M19 39 L55 39 M21 55 L52 55 M21 72 L54 72 M24 89 L50 89"
      fill="none"
      stroke="var(--color-rung)"
      strokeWidth="5"
      strokeLinecap="round"
    />
    <path d="M55 2 C-3 28, 79 78, 21 108" fill="none" stroke="var(--color-brand)" strokeWidth="10" strokeLinecap="round" />
    <path d="M20 2 C78 28, -4 78, 54 108" fill="none" stroke="var(--color-accent)" strokeWidth="10" strokeLinecap="round" />
  </svg>
);

/** Symbol, divider and wordmark kept together as one lockup, as the brand guide asks. */
export const BrandLockup = () => (
  <div className="flex items-center gap-3">
    <BrandSymbol className="h-11 w-8 shrink-0" />
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
