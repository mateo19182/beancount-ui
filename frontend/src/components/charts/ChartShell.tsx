import { Card, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function ChartShell({
  title,
  subtitle,
  children,
  className,
  height = 'h-80',
  action,
}: {
  title: string
  subtitle?: React.ReactNode
  children: React.ReactNode
  className?: string
  height?: string
  action?: React.ReactNode
}) {
  return (
    <Card className={cn('flex flex-col', className)}>
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <CardTitle>{title}</CardTitle>
          {subtitle && <p className="mt-0.5 text-xs text-[var(--color-fg-subtle)]">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className={cn('w-full shrink-0', height)}>{children}</div>
    </Card>
  )
}
