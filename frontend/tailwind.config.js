/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        line: "var(--line)",
        line2: "var(--line-2)",
        txt: "var(--txt)",
        txt2: "var(--txt-2)",
        mute: "var(--mute)",
        lbl: "var(--label)",
        teal: { DEFAULT: "var(--teal)", deep: "var(--teal-deep)", ice: "var(--teal-ice)" },
        lime: "var(--lime)",
        amber: { DEFAULT: "var(--amber)" },
        violet: { DEFAULT: "var(--violet)" },
        sky: { DEFAULT: "var(--sky)" },
        pink: { DEFAULT: "var(--pink)" },
        danger: "var(--red)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
