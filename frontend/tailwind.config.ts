import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f6f8fb",
        ink: "#111827",
        muted: "#667085",
        line: "#d8dee8",
        teal: "#0f766e",
        amber: "#b45309",
        rose: "#be123c",
        indigo: "#4338ca",
        steel: "#334155",
      },
      boxShadow: {
        panel: "0 14px 42px rgba(17, 24, 39, 0.06)",
      },
    },
  },
  plugins: [],
} satisfies Config;
