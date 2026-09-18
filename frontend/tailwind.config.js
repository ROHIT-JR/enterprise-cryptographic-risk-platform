/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Stark, technical charcoal & slate canvas
        ink: {
          950: "#09090b", // deep charcoal (sidebar / high-contrast elements)
          900: "#121316", // refined graphite
          850: "#18181b", // dark neutral
          800: "#27272a", // border on dark
          750: "#3f3f46", // divider on dark
          700: "#71717a", // muted on dark
          200: "#e4e4e7", // light border
          100: "#f4f4f5", // subtle background
          50:  "#fafafa", // canvas background
        },
        // Single precision accent — Deep Indigo
        accent: {
          DEFAULT: "#4f46e5", // Indigo-600
          hover:   "#4338ca", // Indigo-700
          active:  "#3730a3", // Indigo-800
          light:   "#eef2ff", // Indigo-50
          border:  "#c7d2fe", // Indigo-200
        },
        // Monochromatic brand mapping for backwards compatibility
        brand: {
          300: "#4f46e5",
          400: "#4338ca",
          500: "#3730a3",
          600: "#312e81",
        },
        danger: {
          DEFAULT: "#dc2626",
          soft:    "#fef2f2",
          border:  "#fecaca",
          text:    "#991b1b",
        },
        warning: {
          DEFAULT: "#d97706",
          soft:    "#fffbeb",
          border:  "#fde68a",
          text:    "#92400e",
        },
        success: {
          DEFAULT: "#059669",
          soft:    "#ecfdf5",
          border:  "#a7f3d0",
          text:    "#065f46",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["Geist Mono", "JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        popover: "0 4px 12px 0 rgba(0, 0, 0, 0.08), 0 1px 2px 0 rgba(0, 0, 0, 0.04)",
      },
      borderRadius: {
        DEFAULT: "4px",
        sm: "2px",
        md: "4px",
        lg: "6px",
      },
    },
  },
  plugins: [],
};
