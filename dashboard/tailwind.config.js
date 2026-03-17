/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0F172A",
          light: "#1E293B",
          dark: "#020617",
        },
        background: {
          DEFAULT: "#020617",
          secondary: "#0F172A",
          tertiary: "#1E293B",
        },
        cta: {
          DEFAULT: "#22C55E",
          hover: "#16A34A",
          light: "#4ADE80",
        },
        error: {
          DEFAULT: "#EF4444",
          hover: "#DC2626",
          light: "#F87171",
        },
        success: {
          DEFAULT: "#22C55E",
          light: "#4ADE80",
        },
        warning: {
          DEFAULT: "#F59E0B",
          light: "#FCD34D",
        },
        text: {
          primary: "#F8FAFC",
          secondary: "#CBD5E1",
          muted: "#94A3B8", // Updated for WCAG AA compliance
        },
      },
      fontFamily: {
        sans: ["Fira Sans", "system-ui", "sans-serif"],
        mono: ["Fira Code", "monospace"],
      },
      screens: {
        // Tablet-specific breakpoint for precise targeting
        'tablet': '768px',
        // Explicit breakpoints for clarity
        'tablet-only': { 'min': '768px', 'max': '1023px' },
      },
    },
  },
};
