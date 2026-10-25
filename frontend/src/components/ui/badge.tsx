import { cn } from '@/lib/utils'

type BadgeVariant = 'default' | 'income' | 'expense' | 'muted' | 'accent'

const variants: Record<BadgeVariant, string> = {
  default: 'bg-[var(--color-surface-overlay)] text-[var(--color-fg)]',
  income: 'bg-emerald-500/15 text-[var(--color-income)]',
  expense: 'bg-rose-500/15 text-[var(--color-expense)]',
  muted: 'bg-[var(--color-surface-overlay)] text-[var(--color-fg-muted)]',
  accent: 'bg-[var(--color-accent-glow)] text-[var(--color-accent)]',
}

export function Badge({
  variant = 'default',
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium',
        variants[variant],
        className
      )}
      {...props}
    />
  )
}
