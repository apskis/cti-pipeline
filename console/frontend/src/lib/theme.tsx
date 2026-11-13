import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";
export type Theme = "light" | "dark";
/** A company's colour tokens for each theme, by name without the --color- prefix. */
export type BrandTokens = Partial<Record<Theme, Record<string, string>>>;

// public/theme-init.js reads the same key before the page draws.
export const THEME_KEY = "cti-console-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";
// The backend checks these too; the page refuses anything else rather than trusting it.
const TOKEN_NAME = /^[a-z][a-z-]{0,39}$/;
const TOKEN_VALUE = /^#[0-9a-f]{6}$/;

function savedChoice(): ThemeChoice {
  try {
    const saved = window.localStorage.getItem(THEME_KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

function applyChoice(choice: ThemeChoice): void {
  const root = document.documentElement;
  if (choice === "system") delete root.dataset.theme;
  else root.dataset.theme = choice;
}

const systemTheme = (): Theme =>
  typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches ? "dark" : "light";

const resolve = (choice: ThemeChoice, system: Theme): Theme => (choice === "system" ? system : choice);

/**
 * Sets the company's colours for one theme on <html>, over index.css's defaults. Tokens
 * the company leaves out fall back to index.css, so they are removed, not left over from
 * the other theme. `painted` remembers what was set last time.
 */
function paintTokens(tokens: BrandTokens, theme: Theme, painted: Set<string>): void {
  const style = document.documentElement.style;
  const wanted = Object.entries(tokens[theme] ?? {}).filter(
    ([name, value]) => TOKEN_NAME.test(name) && TOKEN_VALUE.test(value),
  );
  const keep = new Set(wanted.map(([name]) => name));
  for (const name of painted) if (!keep.has(name)) style.removeProperty(`--color-${name}`);
  painted.clear();
  for (const [name, value] of wanted) {
    style.setProperty(`--color-${name}`, value);
    painted.add(name);
  }
}

interface ThemeState {
  choice: ThemeChoice;
  /** The theme actually shown, after resolving "system". */
  theme: Theme;
  choose: (choice: ThemeChoice) => void;
  /** Counts brand repaints, so anything that reads tokens once (the chart) can redraw. */
  painting: number;
  setBrandTokens: (tokens: BrandTokens) => void;
}

const ThemeContext = createContext<ThemeState>({
  choice: "system",
  theme: "light",
  choose: () => {},
  painting: 0,
  setBrandTokens: () => {},
});

/** Holds the light, dark or system choice, applies it and the brand colours to <html>. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoice] = useState<ThemeChoice>(savedChoice);
  const [system, setSystem] = useState<Theme>(systemTheme);
  const [painting, setPainting] = useState(0);
  const tokens = useRef<BrandTokens>({});
  const painted = useRef(new Set<string>());
  // Read by the system listener, which is set up once.
  const choiceRef = useRef(choice);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia(DARK_QUERY);
    const follow = () => {
      const next: Theme = query.matches ? "dark" : "light";
      // Painted before the re-render, as in choose(), so the chart reads the new colours.
      paintTokens(tokens.current, resolve(choiceRef.current, next), painted.current);
      setSystem(next);
    };
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, []);

  useEffect(() => applyChoice(choice), [choice]);

  const choose = useCallback((next: ThemeChoice) => {
    // Applied before the re-render, so the chart reads the new colour tokens, not the old.
    applyChoice(next);
    paintTokens(tokens.current, resolve(next, systemTheme()), painted.current);
    choiceRef.current = next;
    setChoice(next);
    try {
      if (next === "system") window.localStorage.removeItem(THEME_KEY);
      else window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Storage blocked: the choice still holds for this visit.
    }
  }, []);

  const setBrandTokens = useCallback((next: BrandTokens) => {
    tokens.current = next;
    paintTokens(next, resolve(choiceRef.current, systemTheme()), painted.current);
    setPainting((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({ choice, theme: resolve(choice, system), choose, painting, setBrandTokens }),
    [choice, system, choose, painting, setBrandTokens],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = (): ThemeState => useContext(ThemeContext);
