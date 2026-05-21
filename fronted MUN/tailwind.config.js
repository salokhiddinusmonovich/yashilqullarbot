/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                stone: {
                    950: '#0c0a09', // Твой глубокий темный фон
                },
            },
        },
    },
    plugins: [],
}