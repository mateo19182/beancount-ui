import { Link, Outlet, useLocation } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const NAV = [
  ['/', 'Overview'],
  ['/charts', 'Charts'],
  ['/investments', 'Investments'],
  ['/crypto', 'Crypto'],
  ['/banks', 'Banks'],
  ['/transactions', 'Transactions'],
  ['/add', 'Add'],
  ['/import', 'Import'],
]

export function Layout() {
  const location = useLocation()
  const qc = useQueryClient()
  const { data: meta } = useQuery({
    queryKey: ['ledger-meta'],
    queryFn: api.ledgerMeta,
    retry: false,
  })

  const reload = useMutation({
    mutationFn: api.reload,
    onSuccess: () => qc.invalidateQueries(),
  })

  const validate = useMutation({ mutationFn: api.validate })
  const prices = useMutation({
    mutationFn: api.updatePrices,
    onSuccess: () => qc.invalidateQueries(),
  })

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-blue-600 text-white dark:border-gray-800">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <span className="text-lg font-bold">Beancount</span>
          <nav className="flex flex-wrap gap-1">
            {NAV.map(([path, label]) => (
              <Link
                key={path}
                to={path}
                className={cn(
                  'rounded px-3 py-1 text-sm no-underline hover:bg-white/20',
                  location.pathname === path && 'bg-white/20'
                )}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={() => prices.mutate()}
              disabled={prices.isPending}
            >
              Prices
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={() => validate.mutate()}
              disabled={validate.isPending}
            >
              Validate
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
              onClick={() => reload.mutate()}
              disabled={reload.isPending}
            >
              Reload
            </Button>
          </div>
        </div>
        {meta && (
          <div className="border-t border-white/20 px-4 py-1 text-xs opacity-80">
            {meta.ledger_path} · {meta.base_currency}
            {meta.error_count > 0 && ` · ${meta.error_count} errors`}
          </div>
        )}
        {(validate.data || prices.data) && (
          <div className="px-4 py-1 text-xs">
            {validate.data && (
              <span className={validate.data.valid ? 'text-green-200' : 'text-red-200'}>
                {validate.data.message}{' '}
              </span>
            )}
            {prices.data && (
              <span className={prices.data.success ? 'text-green-200' : 'text-red-200'}>
                {prices.data.message}
              </span>
            )}
          </div>
        )}
      </header>
      <main className="mx-auto max-w-7xl p-6">
        <Outlet />
      </main>
    </div>
  )
}
