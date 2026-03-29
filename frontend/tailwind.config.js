/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#003087",   // azul corporativo Pluspetrol
          dark:    "#002060",
          light:   "#E8EEF8",
        }
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Menlo", "monospace"],
      }
    }
  },
  plugins: [],
};
