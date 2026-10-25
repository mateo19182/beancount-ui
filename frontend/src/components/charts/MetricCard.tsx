import { Card } from '@/components/ui/card'
import { Money } from '@/lib/privacy-blur'
import { cn } from '@/lib/utils'

type Accent = 'default' | 'income' | 'expense' | 'liability' | 'accent'

const accentStyles: Record<Accent, string> = {
  default: 'text-[var(--color-fg)]',
  income: 'text-[var(--color-income)]',
  expense: 'text-[var(--color-expense)]',
  liability: 'text-[var(--color-liability)]',
  accent: 'text-[var(--color-accent)]',
}

const barStyles: Record<Accent, string> = {
  default: 'bg-[var(--color-fg-muted)]',
  income: 'bg-[var(--color-income)]',
  expense: 'bg-[var(--color-expense)]',
  liability: 'bg-[var(--color-liability)]',
  accent: 'bg-[var(--color-accent)]',
}

export function MetricCard({
  label,
  value,
  sub,
  accent = 'default',
  progress,
  onClick,
  className,
}: {
  label: string
  value: string
  sub?: string
  accent?: Accent
  progress?: number
  onClick?: () => void
  className?: string
}) {
  return (
    <Card
      className={cn(
        'relative overflow-hidden transition-colors',
        onClick && 'cursor-pointer hover:border-[var(--color-accent)]/40',
        className
      )}
      onClick={onClick}
    >
      <div
        className={cn(
          'absolute inset-x-0 top-0 h-px opacity-60',
          accent === 'income' && 'bg-gradient-to-r from-transparent via-emerald-400 to-transparent',
          accent === 'expense' && 'bg-gradient-to-r from-transparent via-rose-400 to-transparent',
          accent === 'accent' && 'bg-gradient-to-r from-transparent via-teal-400 to-transparent',
          accent === 'default' && 'bg-gradient-to-r from-transparent via-[var(--color-fg-subtle)] to-transparent'
        )}
      />
      <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-fg-subtle)]">{label}</p>
      <p className={cn('mt-2 text-2xl font-bold tracking-tight tabular-nums', accentStyles[accent])}>
        <Money>{value}</Money>
      </p>
      {sub && <p className="mt-1 text-xs text-[var(--color-fg-muted)]">{sub}</p>}
      {progress !== undefined && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-[var(--color-surface)]">
          <div
            className={cn('h-full rounded-full transition-all', barStyles[accent])}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </Card>
  )
}
