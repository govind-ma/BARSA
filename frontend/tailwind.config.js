/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        heading: ['"Space Grotesk"', 'Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Standard semantic mapping
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--bg-base)",
        foreground: "var(--text-primary)",
        primary: {
          DEFAULT: "var(--lava-orange)",
          foreground: "#0C0A0B",
        },
        secondary: {
          DEFAULT: "var(--bg-elevated)",
          foreground: "var(--text-primary)",
        },
        destructive: {
          DEFAULT: "var(--lava-red)",
          foreground: "#FFFFFF",
        },
        muted: {
          DEFAULT: "var(--ice-100)",
          foreground: "var(--text-muted)",
        },
        accent: {
          DEFAULT: "var(--ice-200)",
          foreground: "var(--text-primary)",
        },
        card: {
          DEFAULT: "var(--bg-surface)",
          foreground: "var(--text-primary)",
        },
        // Dedicated Ice & Lava tokens
        'bg-base': "var(--bg-base)",
        'bg-surface': "var(--bg-surface)",
        'bg-elevated': "var(--bg-elevated)",
        ice: {
          100: "var(--ice-100)",
          200: "var(--ice-200)",
          300: "var(--ice-300)",
        },
        steel: {
          500: "var(--steel-500)",
          700: "var(--steel-700)",
        },
        'text-primary': "var(--text-primary)",
        'text-secondary': "var(--text-secondary)",
        'text-muted': "var(--text-muted)",
        'border-subtle': "var(--border-subtle)",
        'border-strong': "var(--border-strong)",
        lava: {
          yellow: "var(--lava-yellow)",
          orange: "var(--lava-orange)",
          red: "var(--lava-red)",
          deep: "var(--lava-deep)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        shimmer: {
          "0%": { transform: "translateX(-150%)" },
          "100%": { transform: "translateX(150%)" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: 1, transform: "scale(1)" },
          "50%": { opacity: 0.5, transform: "scale(1.2)" },
        },
        moltenSpin: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        emberRise: {
          "0%": { opacity: 0, transform: "translateY(0) scale(0.6)" },
          "30%": { opacity: 0.8 },
          "100%": { opacity: 0, transform: "translateY(-45px) scale(1.1) translateX(6px)" },
        },
        lavaSweep: {
          "0%": { transform: "translateX(-100%)", opacity: 0 },
          "30%": { opacity: 1 },
          "70%": { opacity: 1 },
          "100%": { transform: "translateX(200%)", opacity: 0 },
        },
      },
      animation: {
        shimmer: "shimmer 2.2s infinite ease-in-out",
        pulseGlow: "pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        moltenSpin: "moltenSpin 6s linear infinite",
        emberRise: "emberRise 3.5s cubic-bezier(0.22, 1, 0.36, 1) infinite",
        lavaSweep: "lavaSweep 1.6s cubic-bezier(0.22, 1, 0.36, 1) infinite",
      },
    },
  },
  plugins: [],
}
