/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./registrations/templates/**/*.html",
    "./dashboard/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#141c27",
        pine: "#163044",
        frost: "#d7e4ef",
      },
      fontFamily: {
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 24px 64px rgba(6, 14, 26, 0.38)",
      },
    },
  },
  plugins: [],
};
