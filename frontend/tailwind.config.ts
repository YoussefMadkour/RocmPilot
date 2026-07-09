import type { Config } from "tailwindcss";

// Starter theme. Jithandra: run the frontend-design skill before expanding this —
// pick an intentional palette (this is a developer "cockpit", lean dark + one
// AMD-adjacent accent) rather than default Tailwind grays.
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
        // Placeholder accent — replace with a deliberate choice.
        accent: "#ed1c24",
      },
    },
  },
  plugins: [],
};

export default config;
