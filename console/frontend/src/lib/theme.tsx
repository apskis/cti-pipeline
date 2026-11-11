import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";
export type Theme = "light" | "dark";

// public/theme-init.js reads the same key before the page draws.
export const THEME_KEY = "cti-console-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

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

interface ThemeState {
  choice: ThemeChoice;
  /** The theme actually shown, after resolving "system". */
  theme: Theme;
  choose: (choice: ThemeChoice) => void;
}

const ThemeContext = createContext<ThemeState>({ choice: "system", theme: "light", choose: () => {} });

/** Holds the light, dark or system choice, applies it to <html>, and remembers it. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoice] = useState<ThemeChoice>(savedChoice);
  const [system, setSystem] = useState<Theme>(systemTheme);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia(DARK_QUERY);
    const follow = () => setSystem(query.matches ? "dark" : "light");
    query.addEventListener("change", follow);
    return () => query.removeEventListener("change", follow);
  }, []);

  useEffect(() => applyChoice(choice), [choice]);

  const choose = useCallback((next: ThemeChoice) => {
    // Applied before the re-render, so the chart reads the new colour tokens, not the old.
    applyChoice(next);
    setChoice(next);
    try {
      if (next === "system") window.localStorage.removeItem(THEME_KEY);
      else window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Storage blocked: the choice still holds for this visit.
    }
  }, []);

  const value = useMemo(
    () => ({ choice, theme: choice === "system" ? system : choice, choose }),
    [choice, system, choose],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = (): ThemeState => useContext(ThemeContext);
