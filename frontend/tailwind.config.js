/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#16212f',
        mist: '#eef3f7',
        steel: '#5f7286',
        signal: '#e86c32',
        aurora: '#0c7b93',
        pine: '#0f766e',
      },
      boxShadow: {
        panel: '0 20px 60px rgba(22, 33, 47, 0.12)',
      },
      backgroundImage: {
        'grid-fade':
          'linear-gradient(rgba(22,33,47,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(22,33,47,0.06) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
};
