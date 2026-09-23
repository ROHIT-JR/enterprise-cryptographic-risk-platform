import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "ecdatx-theme";

function readInitialTheme(): Theme {
  if (typeof document !== "undefined" && document.documentElement.dataset.theme === "dark") return "dark";
  return "light";
}

/**
 * Theme is applied pre-paint by the inline script in index.html (avoids a
 * flash of the wrong theme). This hook just mirrors that state into React
 * and persists changes back to localStorage.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(readInitialTheme);

  const applyTheme = useCallback((next: Theme) => {
    document.documentElement.dataset.theme = next;
    localStorage.setItem(STORAGE_KEY, next);
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    applyTheme(theme === "dark" ? "light" : "dark");
  }, [theme, applyTheme]);

  // Keep in sync if the theme is changed in another tab.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY && (event.newValue === "light" || event.newValue === "dark")) {
        document.documentElement.dataset.theme = event.newValue;
        setThemeState(event.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { theme, setTheme: applyTheme, toggleTheme };
}
