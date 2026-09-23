/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // Design-system tokens live in src/index.css as CSS variables (:root / :root[data-theme="dark"])
      // so components can be theme-aware without a Tailwind rebuild. These Tailwind color aliases just
      // give utility-class access to the same variables (e.g. `bg-accent`, `text-muted`).
      colors: {
        app: "var(--bg-app)",
        card: "var(--bg-card)",
        sidebar: "var(--bg-sidebar)",
        border: "var(--border)",
        ink: "var(--text-primary)",
        muted: "var(--text-muted)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
        },
        risk: {
          critical: "var(--risk-critical)",
          high: "var(--risk-high)",
          medium: "var(--risk-medium)",
          low: "var(--risk-low)",
        },
        "q-safe": "var(--q-safe)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["Geist Mono", "JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        popover: "0 4px 12px 0 rgba(0, 0, 0, 0.08), 0 1px 2px 0 rgba(0, 0, 0, 0.04)",
        panel: "0 1px 2px 0 rgba(0, 0, 0, 0.04), 0 1px 1px 0 rgba(0, 0, 0, 0.03)",
        glow: "0 0 0 1px var(--accent), 0 0 20px -4px var(--accent)",
      },
    },
  },
  plugins: [],
};
