/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07101d",
          900: "#0b1626",
          850: "#102033",
          800: "#14273d",
          750: "#1a2f47",
          700: "#1e3a52",
        },
        brand: {
          300: "#6ee7f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
        },
        danger: {
          DEFAULT: "#ef4444",
          soft: "rgba(239,68,68,0.10)",
          border: "rgba(239,68,68,0.20)",
          text: "#fca5a5",
        },
        warning: {
          DEFAULT: "#f59e0b",
          soft: "rgba(245,158,11,0.10)",
          border: "rgba(245,158,11,0.20)",
          text: "#fcd34d",
        },
        success: {
          DEFAULT: "#22c55e",
          soft: "rgba(34,197,94,0.10)",
          border: "rgba(34,197,94,0.20)",
          text: "#86efac",
        },
      },
      boxShadow: {
        panel: "0 18px 45px rgba(2, 8, 23, 0.24)",
        glow: "0 0 40px rgba(34, 211, 238, 0.14)",
        "glow-danger": "0 0 30px rgba(239,68,68,0.18)",
        "glow-warning": "0 0 30px rgba(245,158,11,0.18)",
      },
    },
  },
  plugins: [],
};

