/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        float: "float 3s ease-in-out infinite",
      },
      colors: {
        bg: 'var(--color-bg)',
        text: 'var(--color-text)',
        border: 'var(--color-border)',
        accent: 'var(--color-accent)',
        hover: 'var(--color-hover)',
        secondary: 'var(--color-secondary)',
      },

      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],     // 12px
        sm: ['0.875rem', { lineHeight: '1.25rem' }], // 14px
        base: ['1rem', { lineHeight: '1.5rem' }],    // 16px
        lg: ['1.125rem', { lineHeight: '1.75rem' }], // 18px
        xl: ['1.25rem', { lineHeight: '1.75rem' }],  // 20px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],   // 24px
      },

      spacing: {
        'icon-xs': '0.875rem', // 14px
        'icon-sm': '1rem',     // 16px
        'icon-md': '1.25rem',  // 20px
        'icon-lg': '1.5rem',   // 24px
        'icon-xl': '2rem',     // 32px
      }
    },
  },
  darkMode: 'class',
};
