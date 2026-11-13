import clsx from "clsx";
import { Monitor, Moon, Sun } from "lucide-react";
import { useLayoutEffect } from "react";

import { useBrand } from "../api/client";
import { type ThemeChoice, useTheme } from "../lib/theme";

// Served by the backend from the company's folder, config/companies/<slug>/.
const SYMBOL_URL = "/api/brand/symbol";
// Shown when the brand file cannot be read, so the page still says what it is.
const FALLBACK_NAME = "CTI console";

/**
 * The company's symbol. A dark mark would vanish on the charcoal page, so in dark mode
 * it can sit on a small tile, coloured by the brand's symbol-tile token.
 */
export const BrandSymbol = ({ className }: { className?: string }) => (
  <span className={clsx("inline-flex shrink-0 items-center justify-center rounded-md bg-symbol-tile p-0.5", className)}>
    <img src={SYMBOL_URL} alt="" aria-hidden className="h-full w-auto" />
  </span>
);

/**
 * Symbol, divider and wordmark kept together as one lockup. Also hands the brand's
 * colours to the theme and names the browser tab after the company.
 */
export const BrandLockup = () => {
  const { data: brand, isError } = useBrand();
  const { setBrandTokens } = useTheme();

  // Layout effect: the colours land before the browser paints the loaded brand.
  useLayoutEffect(() => {
    if (!brand) return;
    setBrandTokens({ light: brand.light, dark: brand.dark });
    document.title = `${brand.name} CTI console`;
  }, [brand, setBrandTokens]);

  const name = brand?.name ?? (isError ? FALLBACK_NAME : "");
  return (
    <div className="flex items-center gap-3">
      {brand ? <BrandSymbol className="h-11" /> : <span aria-hidden className="h-11 w-11" />}
      <span aria-hidden className="h-9 w-px bg-rung" />
      <div className="leading-tight">
        <h1 aria-busy={!brand && !isError} className="min-h-7 text-xl font-semibold tracking-tight text-brand">
          {name}
        </h1>
        <p className="text-[0.7rem] font-medium tracking-[0.12em] text-accent uppercase">
          {brand?.program ?? "Cyber Threat Intelligence"}
        </p>
      </div>
    </div>
  );
};

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
