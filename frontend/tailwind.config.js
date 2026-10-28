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
        // Fixed brand colors (flat, vibrant)
        night: '#141414',
        cream: '#FCEFE6',
        coral: '#F25F5C',
        grape: '#A78BFA',
        teal: '#3CCBB9',
        sun: '#FFE066',
        tangerine: '#F4A261',
        blush: '#FAD1CD',
        // Macro colors
        protein: '#A78BFA',
        carbs: '#FFE066',
        fat: '#F25F5C',
        fiber: '#3CCBB9',
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
