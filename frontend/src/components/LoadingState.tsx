import { Skeleton } from '@/components/ui/skeleton'

export function LoadingState({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-48" />
      ))}
    </div>
  )
}
