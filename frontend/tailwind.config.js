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
          800: "#14273d"
        },
        brand: {
          300: "#6ee7f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2"
        }
      },
      boxShadow: {
        panel: "0 18px 45px rgba(2, 8, 23, 0.24)",
        glow: "0 0 40px rgba(34, 211, 238, 0.14)"
      }
    }
  },
  plugins: []
};

