import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F8FAFC",
        surface: "#FFFFFF",
        border: "#E2E8F0",
        primary: "#00B386",
        heading: "#0F172A",
        secondary: "#64748B",
        muted: "#94A3B8",
        negative: "#EF4444",
        mixed: "#F59E0B",
        positive: "#10B981",
      },
      boxShadow: {
        card: "0 1px 3px rgba(15, 23, 42, 0.08)",
      },
      borderRadius: {
        card: "12px",
        button: "8px",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
