/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	// Standard responsive breakpoints (mobile-first)
  	screens: {
  		'xs': '360px',   // Small phones
  		'sm': '640px',   // Large phones
  		'md': '768px',   // Tablets
  		'lg': '1024px',  // Laptops
  		'xl': '1280px',  // Desktops
  		'2xl': '1536px', // Large screens
  	},
  	extend: {
  		// Safe area spacing
  		spacing: {
  			'safe-top': 'env(safe-area-inset-top)',
  			'safe-bottom': 'env(safe-area-inset-bottom)',
  			'safe-left': 'env(safe-area-inset-left)',
  			'safe-right': 'env(safe-area-inset-right)',
  		},
  		// Min height with dynamic viewport height
  		minHeight: {
  			'screen-dvh': '100dvh',
  			'screen-svh': '100svh',
  		},
  		height: {
  			'screen-dvh': '100dvh',
  			'screen-svh': '100svh',
  		},
  		// Touch target minimum
  		minWidth: {
  			'touch': '44px',
  		},
  		minHeight: {
  			'touch': '44px',
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		// Fluid typography using clamp
  		fontSize: {
  			'fluid-xs': 'clamp(0.75rem, 1.5vw, 0.875rem)',
  			'fluid-sm': 'clamp(0.875rem, 2vw, 1rem)',
  			'fluid-base': 'clamp(1rem, 2.5vw, 1.125rem)',
  			'fluid-lg': 'clamp(1.125rem, 3vw, 1.25rem)',
  			'fluid-xl': 'clamp(1.25rem, 3.5vw, 1.5rem)',
  			'fluid-2xl': 'clamp(1.5rem, 4vw, 2rem)',
  			'fluid-3xl': 'clamp(1.875rem, 5vw, 2.5rem)',
  			'fluid-4xl': 'clamp(2.25rem, 6vw, 3rem)',
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};