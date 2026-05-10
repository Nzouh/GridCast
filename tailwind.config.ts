import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          primary: '#FFFFFF',
          panel: '#F7F8FA',
        },
        text: {
          primary: '#0B0F19',
          secondary: '#6B7280',
          tertiary: '#9CA3AF',
        },
        brand: '#0F3D56',
        border: '#ECEEF2',
        stress: {
          green: 'oklch(0.66 0.16 150)',
          amber: 'oklch(0.78 0.16 78)',
          red: 'oklch(0.62 0.21 27)',
        },
        fan: {
          teal: '#0F3D56',
          outer: 'rgb(15 61 86 / 12%)',
          inner: 'rgb(15 61 86 / 28%)',
          median: '#0F3D56',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jbmono)', '"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};

export default config;
