import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f172a", // slate-900
          raised: "#1e293b", // slate-800
        },
      },
    },
  },
  plugins: [],
};

export default config;
