import { cn } from '@/lib/utils'

export function DataTable({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full text-sm">{children}</table>
    </div>
  )
}

export function DataTableHead({ children }: { children: React.ReactNode }) {
  return (
    <thead>
      <tr className="border-b border-[var(--color-border)] text-left text-xs font-medium uppercase tracking-wider text-[var(--color-fg-subtle)]">
        {children}
      </tr>
    </thead>
  )
}

export function DataTableRow({
  children,
  onClick,
  className,
}: {
  children: React.ReactNode
  onClick?: () => void
  className?: string
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        'border-b border-[var(--color-border-subtle)] transition-colors',
        onClick && 'cursor-pointer hover:bg-[var(--color-surface-overlay)]',
        className
      )}
    >
      {children}
    </tr>
  )
}

export function Th({ children, align = 'left' }: { children: React.ReactNode; align?: 'left' | 'right' }) {
  return (
    <th className={cn('px-2 py-3 font-medium', align === 'right' && 'text-right')}>{children}</th>
  )
}

export function Td({
  children,
  align = 'left',
  className,
}: {
  children: React.ReactNode
  align?: 'left' | 'right'
  className?: string
}) {
  return (
    <td className={cn('px-2 py-3 text-[var(--color-fg)]', align === 'right' && 'text-right tabular-nums', className)}>
      {children}
    </td>
  )
}
