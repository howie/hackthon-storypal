/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // ── heyu-ai Brand Tokens ──────────────────────────────────────
        brand: {
          brown: {
            50:  "#F7F2E9",
            100: "#EEE5D3",
            300: "#CBAC70",
            500: "#A87A45",
            700: "#7B4B32",
            900: "#57382C",
          },
          teal: {
            100: "#C2D9D7",
            300: "#7BA8A4",
            500: "#4F7C78",
            700: "#34514F",
            900: "#283938",
          },
          sage: {
            300: "#C5D9D0",
            500: "#9FB7A7",
          },
          orange: {
            300: "#F8D6B5",
            500: "#E7A36F",
            700: "#EA7842",
          },
          yellow: {
            300: "#FCE8A1",
            500: "#F4C959",
            700: "#D4A220",
          },
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "timeout-pulse": {
          "0%, 100%": {
            borderColor: "hsl(var(--destructive))",
            backgroundColor: "hsl(var(--destructive) / 0.2)",
          },
          "50%": {
            borderColor: "hsl(45 93% 47%)",
            backgroundColor: "hsl(45 93% 47% / 0.2)",
          },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "timeout-pulse": "timeout-pulse 1s ease-in-out infinite",
        "fade-in-up": "fade-in-up 0.8s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
