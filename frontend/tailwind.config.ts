
import type { Config } from "tailwindcss";

export default {
	darkMode: ["class"],
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	theme: {
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		},
		extend: {
			colors: {
				border: 'hsl(var(--border))',
				input: 'hsl(var(--input))',
				ring: 'hsl(var(--ring))',
				background: 'hsl(var(--background))',
				foreground: 'hsl(var(--foreground))',
				primary: {
					DEFAULT: 'hsl(var(--primary))',
					foreground: 'hsl(var(--primary-foreground))'
				},
				secondary: {
					DEFAULT: 'hsl(var(--secondary))',
					foreground: 'hsl(var(--secondary-foreground))'
				},
				destructive: {
					DEFAULT: 'hsl(var(--destructive))',
					foreground: 'hsl(var(--destructive-foreground))'
				},
				muted: {
					DEFAULT: 'hsl(var(--muted))',
					foreground: 'hsl(var(--muted-foreground))'
				},
				accent: {
					DEFAULT: 'hsl(var(--accent))',
					foreground: 'hsl(var(--accent-foreground))'
				},
				popover: {
					DEFAULT: 'hsl(var(--popover))',
					foreground: 'hsl(var(--popover-foreground))'
				},
				card: {
					DEFAULT: 'hsl(var(--card))',
					foreground: 'hsl(var(--card-foreground))'
				},
				sidebar: {
					DEFAULT: 'hsl(var(--sidebar-background))',
					foreground: 'hsl(var(--sidebar-foreground))',
					primary: 'hsl(var(--sidebar-primary))',
					'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
					accent: 'hsl(var(--sidebar-accent))',
					'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
					border: 'hsl(var(--sidebar-border))',
					ring: 'hsl(var(--sidebar-ring))'
				},
				// 子ども向けパステルカラー
				'lavender-light': '#F3F0FF',
				'lavender-soft': '#C4B5FD',
				'mint-light': '#F0FDF4',
				'mint-soft': '#86EFAC',
				'sky-light': '#F0F9FF',
				'sky-soft': '#93C5FD',
				'pink-soft': '#F9A8D4',
				'purple-soft': '#C084FC',
				'navy-dark': '#2A2A44',
				// 子ども向けテーマカラー
				'kid-pink': '#FFB7C5',
				'kid-blue': '#87CEEB',
				'kid-yellow': '#FFE135',
				'kid-green': '#98FB98',
				'kid-purple': '#DDA0DD',
				'kid-orange': '#FFB347'
			},
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)'
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
				},
				'bounce-gentle': {
					'0%, 100%': {
						transform: 'translateY(0)',
						animationTimingFunction: 'cubic-bezier(0.8, 0, 1, 1)'
					},
					'50%': {
						transform: 'translateY(-10px)',
						animationTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)'
					}
				},
				'wiggle': {
					'0%, 100%': { transform: 'rotate(-3deg)' },
					'50%': { transform: 'rotate(3deg)' }
				},
				'pulse-gentle': {
					'0%, 100%': { transform: 'scale(1)' },
					'50%': { transform: 'scale(1.05)' }
				},
				'float': {
					'0%, 100%': { transform: 'translateY(0px)' },
					'50%': { transform: 'translateY(-20px)' }
				},
				'char-idle': {
					'0%, 100%': { transform: 'translateY(0)' },
					'50%': { transform: 'translateY(-8px)' }
				},
				'char-walking': {
					'0%, 100%': { transform: 'translateX(0)' },
					'25%': { transform: 'translateX(-6px)' },
					'75%': { transform: 'translateX(6px)' }
				},
				'char-cheering': {
					'0%, 100%': { transform: 'translateY(0) scale(1)' },
					'40%': { transform: 'translateY(-14px) scale(1.04)' },
					'60%': { transform: 'translateY(-6px) scale(1.02)' }
				},
				'char-celebrating': {
					'0%, 100%': { transform: 'scale(1) rotate(0deg)' },
					'25%': { transform: 'scale(1.06) rotate(-2deg)' },
					'75%': { transform: 'scale(1.06) rotate(2deg)' }
				},
				'char-sleeping': {
					'0%, 100%': { opacity: '1' },
					'50%': { opacity: '0.85' }
				},
				'experience-fill': {
					'0%': { width: '0%' },
					'100%': { width: 'var(--experience-width)' }
				}
			},
			animation: {
				'accordion-down': 'accordion-down 0.2s ease-out',
				'accordion-up': 'accordion-up 0.2s ease-out',
				'bounce-gentle': 'bounce-gentle 2s infinite',
				'wiggle': 'wiggle 1s ease-in-out infinite',
				'pulse-gentle': 'pulse-gentle 2s infinite',
				'float': 'float 3s ease-in-out infinite',
				'char-idle': 'char-idle 2.8s ease-in-out infinite',
				'char-walking': 'char-walking 0.9s ease-in-out infinite',
				'char-cheering': 'char-cheering 0.7s ease-in-out infinite',
				'char-celebrating': 'char-celebrating 1.2s ease-in-out infinite',
				'char-sleeping': 'char-sleeping 2.5s ease-in-out infinite',
				'experience-fill': 'experience-fill 1s ease-out'
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
} satisfies Config;
