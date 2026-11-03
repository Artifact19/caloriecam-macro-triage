/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Theme-aware tokens (flip in dark mode via CSS variables in index.css)
        page: 'var(--c-page)',
        surface: 'var(--c-surface)',
        sunken: 'var(--c-sunken)',
        ink: 'var(--c-ink)',
        muted: 'var(--c-muted)',
        panel: 'var(--c-panel)',
        // Fixed brand colors (warm Neo-Brutalism palette)
        night: '#1C1917',
        cream: '#F7F5F0',
        coral: '#D97762',
        grape: '#9688B0',
        teal: '#869874',
        sun: '#EAB252',
        tangerine: '#DE8E48',
        blush: '#E6CFCA',
        // Macro colors
        protein: '#9688B0',
        carbs: '#EAB252',
        fat: '#D97762',
        fiber: '#869874',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'brutal-sm': '2px 2px 0 0 var(--c-ink)',
        brutal: '4px 4px 0 0 var(--c-ink)',
        'brutal-lg': '6px 6px 0 0 var(--c-ink)',
        'brutal-xl': '8px 8px 0 0 var(--c-ink)',
        'brutal-none': '0 0 0 0 var(--c-ink)',
      },
      borderWidth: {
        3: '3px',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        stripes: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '40px 0' },
        },
        bob: {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '50%': { transform: 'translateY(-6px) rotate(8deg)' },
        },
      },
      animation: {
        shimmer: 'shimmer 2.4s linear infinite',
        stripes: 'stripes 1s linear infinite',
        bob: 'bob 4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
