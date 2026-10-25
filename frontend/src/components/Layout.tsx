import { Link, Outlet, useLocation } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  LayoutDashboard,
  BarChart3,
  TrendingUp,
  Bitcoin,
  Landmark,
  List,
  PlusCircle,
  Download,
  RefreshCw,
  Sparkles,
  EyeOff,
  Eye,
} from 'lucide-react'
import { api } from '@/api/client'
import { usePrivacyBlur } from '@/lib/privacy-blur'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const NAV = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/charts', label: 'Analytics', icon: BarChart3 },
  { path: '/investments', label: 'Investments', icon: TrendingUp },
  { path: '/crypto', label: 'Crypto', icon: Bitcoin },
  { path: '/banks', label: 'Banks', icon: Landmark },
  { path: '/transactions', label: 'Transactions', icon: List },
  { path: '/add', label: 'New entry', icon: PlusCircle },
  { path: '/import', label: 'Import', icon: Download },
]

export function Layout() {
  const location = useLocation()
  const qc = useQueryClient()
  const { blurAmounts, toggleBlurAmounts } = usePrivacyBlur()
  const { data: meta } = useQuery({
    queryKey: ['ledger-meta'],
    queryFn: api.ledgerMeta,
    retry: false,
  })

  const reload = useMutation({
    mutationFn: api.reload,
    onSuccess: () => qc.invalidateQueries(),
  })

  const ledgerName = meta?.ledger_path?.split('/').pop() ?? 'Ledger'
  const statusMsg = reload.data?.message
  const statusOk = reload.data?.valid

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-56 shrink-0 flex-col border-r border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)]">
        <div className="border-b border-[var(--color-border-subtle)] px-4 py-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-accent-glow)]">
              <Sparkles className="h-4 w-4 text-[var(--color-accent)]" />
            </div>
            <div>
              <p className="text-sm font-bold tracking-tight">Ledger</p>
              <p className="truncate text-[10px] text-[var(--color-fg-subtle)]" title={meta?.ledger_path}>
                {ledgerName}
              </p>
            </div>
          </div>
          {meta && (
            <div className="mt-3 flex flex-wrap gap-1">
              <Badge variant="accent">{meta.base_currency}</Badge>
              {meta.error_count > 0 && (
                <Badge variant="expense">{meta.error_count} errors</Badge>
              )}
            </div>
          )}
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {NAV.map(({ path, label, icon: Icon }) => {
            const active = location.pathname === path
            return (
              <Link
                key={path}
                to={path}
                className={cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm no-underline transition-colors',
                  active
                    ? 'bg-[var(--color-accent-glow)] font-medium text-[var(--color-accent)]'
                    : 'text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-fg)]'
                )}
              >
                <Icon className="h-4 w-4 shrink-0 opacity-80" />
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="border-t border-[var(--color-border-subtle)] p-3 space-y-1">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={toggleBlurAmounts}
            aria-pressed={blurAmounts}
          >
            {blurAmounts ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
            {blurAmounts ? 'Show amounts' : 'Blur amounts'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => reload.mutate()}
            disabled={reload.isPending}
          >
            <RefreshCw className={cn('h-3.5 w-3.5', reload.isPending && 'animate-spin')} />
            Reload
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {statusMsg && (
          <div
            className={cn(
              'border-b px-6 py-2 text-xs',
              statusOk
                ? 'border-emerald-500/20 bg-emerald-500/10 text-[var(--color-income)]'
                : 'border-rose-500/20 bg-rose-500/10 text-[var(--color-expense)]'
            )}
          >
            {statusMsg}
          </div>
        )}
        <main className="flex-1 p-6 lg:p-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
