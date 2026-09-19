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
        // 企业控制台用紧凑圆角：卡片 10px、面板 12px、控件 8px。
        // 之前到处用 rounded-2xl（16px）会显得像消费级 App。
        control: '8px',
        card: '10px',
        panel: '12px',
      },
      fontSize: {
        // 统一字号阶梯，避免出现 13px/15px 这类随手写的尺寸
        micro: ['11px', { lineHeight: '16px' }],
        caption: ['12px', { lineHeight: '18px' }],
        ui: ['13px', { lineHeight: '20px' }],
        body: ['14px', { lineHeight: '22px' }],
        lead: ['15px', { lineHeight: '26px' }],
        title: ['17px', { lineHeight: '26px', letterSpacing: '-0.01em' }],
        display: ['22px', { lineHeight: '30px', letterSpacing: '-0.02em' }],
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
        // 控制台靠 1px 描边分隔层次，阴影只用在浮起元素（输入区、下拉）
        soft: '0 1px 2px rgba(15, 23, 42, 0.04)',
        panel: '0 1px 2px rgba(15, 23, 42, 0.04)',
        composer:
          '0 1px 2px rgba(15, 23, 42, 0.04), 0 12px 28px rgba(15, 23, 42, 0.06)',
      },
      spacing: {
        18: '4.5rem',
      },
    },
  },
  plugins: [],
}
