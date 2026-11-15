/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#7185D1",
          secondary: "#E5E9FF",
          background: "#F4F6FC",
          card: "#FFFFFF",
          text: "#20243A",
          accent: "#FF8D86",
          darkPeriwinkle: "#576BB9",
          muted: "#8A94A6",
          border: "#E2E8F0"
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1.25rem',
        '3xl': '1.75rem',
        '4xl': '2.25rem'
      },
      boxShadow: {
        'soft': '0 8px 30px rgba(113, 133, 209, 0.08)',
        'card': '0 4px 20px rgba(32, 36, 58, 0.05)',
        'elevated': '0 12px 35px rgba(113, 133, 209, 0.16)'
      }
    },
  },
  plugins: [],
}
