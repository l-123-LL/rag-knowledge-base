/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
        ink: {
          950: '#020617',
          900: '#0f172a',
          700: '#334155',
          600: '#475569',
          500: '#64748b',
          400: '#94a3b8',
        },
        line: '#e2e8f0',
        surface: '#ffffff',
        mist: '#f8fafc',
        canvas: '#f1f5f9',
        sidebar: '#0b1220',
        success: '#059669',
        warning: '#d97706',
        danger: '#dc2626',
      },
      borderRadius: {
        card: '10px',
        panel: '14px',
      },
      fontFamily: {
        sans: [
          'Inter',
          'PingFang SC',
          'Microsoft YaHei',
          'system-ui',
          'sans-serif',
        ],
      },
      boxShadow: {
        soft: '0 12px 32px rgba(15, 23, 42, 0.08)',
        panel: '0 1px 2px rgba(15, 23, 42, 0.04), 0 12px 28px rgba(15, 23, 42, 0.06)',
        composer: '0 18px 45px rgba(15, 23, 42, 0.12)',
      },
      spacing: {
        18: '4.5rem',
      },
    },
  },
  plugins: [],
}
