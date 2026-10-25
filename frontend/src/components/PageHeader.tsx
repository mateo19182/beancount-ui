import { cn } from '@/lib/utils'

export function PageHeader({
  title,
  description,
  action,
  className,
}: {
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-4', className)}>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--color-fg)]">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-[var(--color-fg-muted)]">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
