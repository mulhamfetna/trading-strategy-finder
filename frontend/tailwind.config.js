/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        tv: {
          bg: '#131722',
          surface: '#1e222d',
          tile: '#2a2e39',
          border: '#363a45',
          text: '#d1d4dc',
          muted: '#787b86',
          green: '#00c853',
          red: '#ff5252',
          blue: '#2962ff',
          orange: '#ff9800',
        },
      },
    },
  },
  plugins: [],
};
