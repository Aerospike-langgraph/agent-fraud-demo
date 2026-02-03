/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme inspired by terminal/IDE aesthetics
        bg: {
          primary: '#0d1117',
          secondary: '#161b22',
          tertiary: '#21262d',
          elevated: '#30363d',
        },
        accent: {
          cyan: '#58a6ff',
          green: '#3fb950',
          red: '#f85149',
          orange: '#d29922',
          purple: '#a371f7',
          pink: '#db61a2',
        },
        text: {
          primary: '#e6edf3',
          secondary: '#8b949e',
          muted: '#6e7681',
        },
        border: {
          default: '#30363d',
          muted: '#21262d',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(88, 166, 255, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(88, 166, 255, 0.8)' },
        },
      },
    },
  },
  plugins: [],
}
