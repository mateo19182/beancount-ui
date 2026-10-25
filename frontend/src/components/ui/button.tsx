import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all duration-150 disabled:pointer-events-none disabled:opacity-40',
  {
    variants: {
      variant: {
        default:
          'bg-[var(--color-accent)] text-[#0c0e12] hover:bg-[var(--color-accent-dim)] shadow-[0_0_20px_var(--color-accent-glow)]',
        outline:
          'border border-[var(--color-border)] bg-transparent text-[var(--color-fg)] hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-glow)]',
        ghost: 'text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-fg)]',
        destructive: 'bg-[var(--color-expense)] text-white hover:opacity-90',
        subtle: 'bg-[var(--color-surface-overlay)] text-[var(--color-fg)] hover:bg-[var(--color-border)]',
      },
      size: {
        default: 'h-9 px-4',
        sm: 'h-8 px-3 text-xs',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    )
  }
)
Button.displayName = 'Button'
