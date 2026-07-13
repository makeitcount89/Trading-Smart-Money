import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: {
          950: "#05070d",
          900: "#0a0e17",
          850: "#0f1420",
          800: "#141a29",
          700: "#1e2638",
          600: "#2b3448",
          500: "#4a5468",
        },
        long: {
          DEFAULT: "#22c55e",
          muted: "#14532d",
        },
        short: {
          DEFAULT: "#f43f5e",
          muted: "#4c0519",
        },
        accent: {
          DEFAULT: "#38bdf8",
          muted: "#0c4a6e",
        },
        // Matches LuxAlgo's default bullish order block colors
        // (internalBullishOrderBlockColor #3179f5 / swingBullishOrderBlockColor #1848cc).
        smcBlue: {
          DEFAULT: "#3179f5",
          muted: "#12294f",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
