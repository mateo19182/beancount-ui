import { ArrowDownLeft, ArrowUpRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Flow } from '@/lib/flow'

interface FlowToggleProps {
  value: Flow
  onChange: (flow: Flow) => void
  className?: string
  size?: 'sm' | 'md'
}

export function FlowToggle({ value, onChange, className, size = 'sm' }: FlowToggleProps) {
  const btn = size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-sm'

  return (
    <div
      className={cn(
        'inline-flex rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-0.5',
        className
      )}
      role="group"
      aria-label="Money flow"
    >
      <button
        type="button"
        className={cn(
          'inline-flex items-center gap-1 rounded-md font-medium transition-colors',
          btn,
          value === 'out'
            ? 'bg-[var(--color-expense)]/15 text-[var(--color-expense)]'
            : 'text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]'
        )}
        onClick={() => onChange('out')}
      >
        <ArrowDownLeft className="h-3.5 w-3.5" />
        Out
      </button>
      <button
        type="button"
        className={cn(
          'inline-flex items-center gap-1 rounded-md font-medium transition-colors',
          btn,
          value === 'in'
            ? 'bg-[var(--color-income)]/15 text-[var(--color-income)]'
            : 'text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]'
        )}
        onClick={() => onChange('in')}
      >
        <ArrowUpRight className="h-3.5 w-3.5" />
        In
      </button>
    </div>
  )
}
