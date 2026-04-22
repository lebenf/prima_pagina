/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#f0f4ff',
          500: '#3b5bdb',
          600: '#364fc7',
          700: '#2f44ad',
          900: '#1a1a2e',
        },
        newspaper: {
          bg:     '#faf9f7',
          text:   '#1a1a1a',
          border: '#d4c5b0',
          accent: '#8b0000',
        },
      },
      fontFamily: {
        serif: ['Georgia', 'Times New Roman', 'serif'],
        sans:  ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
