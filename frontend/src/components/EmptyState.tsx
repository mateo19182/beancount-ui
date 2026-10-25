import { cn } from '@/lib/utils'

export function EmptyState({
  title,
  description,
  className,
}: {
  title: string
  description?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] py-16 text-center',
        className
      )}
    >
      <p className="text-sm font-medium text-[var(--color-fg-muted)]">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-xs text-[var(--color-fg-subtle)]">{description}</p>
      )}
    </div>
  )
}
