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
        stress: {
          green: '#16A34A',
          amber: '#F59E0B',
          red: '#DC2626',
        },
        fan: {
          teal: 'rgb(15 61 86)',
          outer: 'rgb(15 61 86 / 12%)',
          inner: 'rgb(15 61 86 / 28%)',
          median: 'rgb(15 61 86)',
        },
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
