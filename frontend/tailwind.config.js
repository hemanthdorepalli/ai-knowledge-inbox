/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Black + white + orange
        app: "#ffffff", // main chat background
        sidebar: "#141414", // black sidebar
        panel: "#f5f4f2", // light neutral fill (modal inputs, source cards)
        card: "#ffffff",
        ink: "#141414", // near-black text on white
        muted: "#6b6b6b",
        faint: "#9a9a9a",
        line: "#e7e5e2",
        accent: {
          DEFAULT: "#f97316", // orange
          hover: "#ea580c",
          soft: "#fff2e6",
        },
        user: "#141414", // black user-message bubble
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["Fraunces", "ui-serif", "Georgia", "serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(20, 20, 20, 0.05), 0 4px 16px rgba(20, 20, 20, 0.06)",
        lift: "0 8px 30px rgba(20, 20, 20, 0.14)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.8s linear infinite",
      },
    },
  },
  plugins: [],
};
