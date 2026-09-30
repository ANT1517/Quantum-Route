/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 700: "#1e2a4a", 800: "#152040", 900: "#0b1530" },
        teal: { DEFAULT: "#0d9488" },
        congestion: "#f59e0b",
      },
    },
  },
  plugins: [],
};
