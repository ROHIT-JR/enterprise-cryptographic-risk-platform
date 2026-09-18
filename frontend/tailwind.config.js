/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // "ink" palette — now maps to light grays (inverted from dark theme)
        ink: {
          950: "#f8fafc",  // page background (slate-50)
          900: "#ffffff",  // sidebar / card background
          850: "#f1f5f9",  // subtle hover / input bg (slate-100)
          800: "#e2e8f0",  // borders (slate-200)
          750: "#cbd5e1",  // dividers (slate-300)
          700: "#94a3b8",  // muted text (slate-400)
        },
        // "brand" palette — now a professional, readable blue
        brand: {
          300: "#2563eb",  // primary accent (blue-600) — readable on white
          400: "#3b82f6",  // interactive blue (blue-500)
          500: "#60a5fa",  // lighter blue for bg tints (blue-400)
          600: "#93c5fd",  // very light blue tint (blue-300)
        },
        danger: {
          DEFAULT: "#ef4444",
          soft:    "#fef2f2",
          border:  "#fecaca",
          text:    "#b91c1c",
        },
        warning: {
          DEFAULT: "#f59e0b",
          soft:    "#fffbeb",
          border:  "#fde68a",
          text:    "#92400e",
        },
        success: {
          DEFAULT: "#22c55e",
          soft:    "#f0fdf4",
          border:  "#bbf7d0",
          text:    "#166534",
        },
      },
      boxShadow: {
        panel: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        glow:  "0 4px 12px rgba(59,130,246,0.15)",
        "glow-danger":  "0 4px 12px rgba(239,68,68,0.15)",
        "glow-warning": "0 4px 12px rgba(245,158,11,0.12)",
      },
    },
  },
  plugins: [],
};
