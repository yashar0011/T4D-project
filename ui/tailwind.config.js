/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],

  /* top-level tokens → bg-background / text-foreground / border-border … */
  theme: {
    colors: {
      background:  'hsl(var(--background) / <alpha-value>)',
      foreground:  'hsl(var(--foreground) / <alpha-value>)',
      border:      'hsl(var(--border) / <alpha-value>)',
      input:       'hsl(var(--input) / <alpha-value>)',
      ring:        'hsl(var(--ring) / <alpha-value>)',
      muted:       'hsl(var(--muted) / <alpha-value>)',
      accent:      'hsl(var(--accent) / <alpha-value>)',
      destructive: 'hsl(var(--destructive) / <alpha-value>)',
    },
    extend: {
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      /* nested palettes – still usable via utilities like bg-card */
      colors: {
        card:    { DEFAULT: 'hsl(var(--card) / <alpha-value>)',
                   foreground: 'hsl(var(--card-foreground) / <alpha-value>)' },
        popover: { DEFAULT: 'hsl(var(--popover) / <alpha-value>)',
                   foreground: 'hsl(var(--popover-foreground) / <alpha-value>)' },
        primary: { DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
                   foreground: 'hsl(var(--primary-foreground) / <alpha-value>)' },
        secondary:{ DEFAULT:'hsl(var(--secondary) / <alpha-value>)',
                    foreground:'hsl(var(--secondary-foreground) / <alpha-value>)'},
        chart: {
          1: 'hsl(var(--chart-1) / <alpha-value>)',
          2: 'hsl(var(--chart-2) / <alpha-value>)',
          3: 'hsl(var(--chart-3) / <alpha-value>)',
          4: 'hsl(var(--chart-4) / <alpha-value>)',
          5: 'hsl(var(--chart-5) / <alpha-value>)',
        },
      },
    },
  },

  plugins: [require('tailwindcss-animate')],
};
