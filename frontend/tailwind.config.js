/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // MAX 2025 모던 블랙 & 화이트 테마
        primary: {
          50: '#fafafa',   // 거의 흰색
          100: '#f5f5f5',  // 매우 연한 회색
          200: '#e5e5e5',  // 연한 회색
          300: '#d4d4d4',  // 중간 연한 회색
          400: '#a3a3a3',  // 중간 회색
          500: '#737373',  // 중간 진한 회색
          600: '#525252',  // 진한 회색
          700: '#404040',  // 매우 진한 회색
          800: '#262626',  // 거의 검은색
          900: '#171717',  // 순수 검은색
        },
        accent: {
          50: '#f8fafc',   // 매우 연한 블루그레이
          100: '#f1f5f9',  // 연한 블루그레이
          200: '#e2e8f0',  // 중간 연한 블루그레이
          300: '#cbd5e1',  // 중간 블루그레이
          400: '#94a3b8',  // 진한 블루그레이
          500: '#64748b',  // 매우 진한 블루그레이 (메인 액센트)
          600: '#475569',  // 다크 블루그레이
          700: '#334155',  // 매우 다크 블루그레이
          800: '#1e293b',  // 거의 검은 블루그레이
          900: '#0f172a',  // 순수 다크 블루그레이
        },
        neutral: {
          50: '#fafafa',   // 순수 흰색
          100: '#f5f5f5',  // 매우 연한 회색
          200: '#e5e5e5',  // 연한 회색
          300: '#d4d4d4',  // 중간 연한 회색
          400: '#a3a3a3',  // 중간 회색
          500: '#737373',  // 중간 진한 회색
          600: '#525252',  // 진한 회색
          700: '#404040',  // 매우 진한 회색
          800: '#262626',  // 거의 검은색
          900: '#171717',  // 순수 검은색
        },
        surface: {
          light: '#ffffff',     // 순수 흰색 배경
          card: '#fafafa',      // 카드 배경
          elevated: '#f5f5f5',  // 높은 카드 배경
          dark: '#171717',      // 다크 배경
          'dark-card': '#262626', // 다크 카드 배경
        }
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #171717 0%, #404040 100%)',
        'gradient-accent': 'linear-gradient(135deg, #64748b 0%, #334155 100%)',
        'gradient-light': 'linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%)',
        'gradient-dark': 'linear-gradient(135deg, #262626 0%, #171717 100%)',
      },
      boxShadow: {
        'minimal': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'soft': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'medium': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'large': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'inner-light': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
        'glow': '0 0 20px rgba(100, 116, 139, 0.15)',
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'display': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1' }],
        '6xl': ['3.75rem', { lineHeight: '1' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(100, 116, 139, 0.1)' },
          '100%': { boxShadow: '0 0 30px rgba(100, 116, 139, 0.2)' },
        },
      },
    },
  },
  plugins: [],
} 