import type { Config } from "tailwindcss";

// Theme tokens come from frontend/DESIGN.md ("engine-bay cockpit").
// Don't add colors ad hoc — extend the doc first.
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bay: "#141014", // page background — red-warmed dark, not neutral gray
        panel: "#1C1519", // cards, rail
        edge: "#2B2026", // borders, dividers
        accent: "#ED1C24", // AMD signal red — interactive + brand only
        ember: "#FF8A3D", // in-progress, caution, replay badge
        ready: "#3DDC97", // pass / done
        ink: "#F2EDEE",
        "ink-dim": "#A89DA2",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        sans: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
