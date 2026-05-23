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
          // Error-state tokens used by FilePicker.vue. Pre-mixed against
          // the dark tv-bg so they read as "muted error" rather than the
          // shouty Tailwind red palette.
          'error-bg':     '#3a0c12',   // tv-red mixed with tv-bg (dark)
          'error-ring':   '#ff5252',   // = tv-red, full strength
          'error-text':   '#ff8a8a',   // tv-red lightened for readable text on dark
          'error-text-hover': '#ffcccc',
        },
      },
    },
  },
  plugins: [],
};
