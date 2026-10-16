/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        slate: {
          950: '#07080a', // --bg
          900: '#0e1013', // --panel
          850: '#14171b', // --panel2
          800: '#1a1e24',
          750: '#222730',
          700: '#2b1416', // --border
          600: '#3d1b1e',
          500: '#8a8f98', // --muted
          400: '#9ea3ac',
          300: '#cbd0d8',
          200: '#e0e4eb',
          100: '#e8eaed', // --text
        },
        teal: {
          300: '#ff9496', // Light red for chip text
          400: '#f87171',
          500: '#ef2b2d', // --accent
          600: '#dc2626',
          700: '#b91c1c',
          900: '#7f1d1d', // --accent-dim
          950: '#3b0d0e',
        },
        amber: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        },
        emerald: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          950: '#06281c',
        },
        rose: {
          400: '#f87171',
          500: '#ef2b2d',
          600: '#dc2626',
          950: '#3b0d0e',
        }
      },
      fontFamily: {
        heading: ['"Rajdhani"', '"Roboto Condensed"', '"Arial Narrow"', 'system-ui', 'sans-serif'],
        sans: ['"Roboto Condensed"', '"Rajdhani"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'Consolas', 'Courier New', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2.5s cubic-bezier(0, 0, 0.2, 1) infinite',
        'red-pulse': 'red-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
