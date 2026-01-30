/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Primary - Professional Medical Blue
        primary: {
          50: "#f0f7fc",
          100: "#e1f0f9",
          200: "#bde0f3",
          300: "#8acae9",
          400: "#52b1db",
          500: "#2d96c6",
          600: "#1e7aa8",
          700: "#1a6289",
          800: "#1a5271",
          900: "#1b455e",
        },
        // Accent - Fresh Mint/Teal (Dental Hygiene)
        accent: {
          50: "#effcfb",
          100: "#d7f7f5",
          200: "#b3f0ec",
          300: "#7ee4de",
          400: "#43cec6",
          500: "#28b5ad",
          600: "#1f9290",
          700: "#1e7574",
          800: "#1e5d5c",
          900: "#1d4d4c",
        },
        // Warm - Soft Coral (Approachability)
        warm: {
          50: "#fef7f4",
          100: "#fdeee8",
          200: "#fcdcd0",
          300: "#f9c2ad",
          400: "#f4a07f",
          500: "#ec7d54",
          600: "#dc6339",
          700: "#b84e2d",
          800: "#98422a",
          900: "#7c3a27",
        },
        // Medical Design System aliases
        dental: {
          primary: "#2d96c6",
          accent: "#28b5ad",
          warm: "#ec7d54",
          dark: "#1e293b",
          muted: "#64748b",
          light: "#f8fafc",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Monaco", "Consolas", "monospace"],
      },
      boxShadow: {
        "xs": "0 1px 2px 0 rgba(0, 0, 0, 0.03)",
        "primary": "0 4px 14px rgba(45, 150, 198, 0.25)",
        "primary-lg": "0 8px 25px rgba(45, 150, 198, 0.3)",
        "accent": "0 4px 14px rgba(40, 181, 173, 0.25)",
        "accent-lg": "0 8px 25px rgba(40, 181, 173, 0.3)",
        "glow": "0 0 20px rgba(45, 150, 198, 0.2)",
        "glow-accent": "0 0 20px rgba(40, 181, 173, 0.2)",
        "inner-sm": "inset 0 1px 2px rgba(0, 0, 0, 0.05)",
      },
      borderRadius: {
        "2xl": "1.25rem",
        "3xl": "1.5rem",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out forwards",
        "fade-in-up": "fadeInUp 0.5s ease-out forwards",
        "fade-in-scale": "fadeInScale 0.4s ease-out forwards",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "spin-slow": "spin 3s linear infinite",
        "bounce-subtle": "bounce-subtle 1.5s ease-in-out infinite",
        "bounce-gentle": "bounce-gentle 2s ease-in-out infinite",
        "breathe": "breathe 4s ease-in-out infinite",
        "float": "float 6s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeInScale: {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(45, 150, 198, 0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(45, 150, 198, 0)" },
        },
        "bounce-subtle": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
        "bounce-gentle": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        breathe: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.8" },
          "50%": { transform: "scale(1.05)", opacity: "1" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
    },
  },
  plugins: [],
};
