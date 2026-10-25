import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { PageHeader } from '@/components/PageHeader'
import { LoadingState } from '@/components/LoadingState'
import { MetricCard } from '@/components/charts/MetricCard'
import { ChartShell } from '@/components/charts/ChartShell'
import { CategoryBars } from '@/components/charts/CategoryBars'
import { DataTable, DataTableHead, DataTableRow, Th, Td } from '@/components/DataTable'
import { Card, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatMoney } from '@/lib/utils'
import { FormattedMoney, Money } from '@/lib/privacy-blur'
import { cn } from '@/lib/utils'

export function BanksPage() {
  const [tab, setTab] = useState<'balances' | 'files'>('balances')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  const { data: balances, isLoading: balLoading, error: balError } = useQuery({
    queryKey: ['bank-balances'],
    queryFn: api.bankBalances,
  })
  const { data: files } = useQuery({ queryKey: ['bank-files'], queryFn: api.bankFiles })
  const { data: fileContent } = useQuery({
    queryKey: ['bank-file', selectedFile],
    queryFn: () => api.bankFile(selectedFile!),
    enabled: !!selectedFile,
  })

  const barData =
    balances?.accounts.map((a) => ({ name: a.account.split(':').pop() ?? a.account, total: a.value })) ?? []

  return (
    <div className="space-y-8">
      <PageHeader title="Banks" description="Cash accounts and import files" />

      <div className="inline-flex rounded-lg border border-[var(--color-border)] p-1">
        {(['balances', 'files'] as const).map((t) => (
          <Button
            key={t}
            variant="ghost"
            size="sm"
            className={cn(
              tab === t && 'bg-[var(--color-accent-glow)] text-[var(--color-accent)]'
            )}
            onClick={() => setTab(t)}
          >
            {t === 'balances' ? 'Balances' : 'Import files'}
          </Button>
        ))}
      </div>

      {tab === 'balances' && (
        <>
          {balLoading && <LoadingState rows={1} />}
          {balError && <p className="text-[var(--color-expense)]">{String(balError)}</p>}
          {balances && (
            <div className="space-y-6">
              <MetricCard
                label="Total cash"
                value={formatMoney(balances.total, balances.currency)}
                accent="accent"
              />

              {barData.length > 0 && (
                <ChartShell title="By account" height="h-64">
                  <CategoryBars
                    data={barData}
                    currency={balances.currency}
                    layout="horizontal"
                  />
                </ChartShell>
              )}

              <ChartShell title="Account details" height="h-auto">
                <DataTable>
                  <DataTableHead>
                    <Th>Account</Th>
                    <Th align="right">Balance</Th>
                  </DataTableHead>
                  <tbody>
                    {balances.accounts.map((acc) => (
                      <DataTableRow key={acc.account}>
                        <Td>
                          <details className="group">
                            <summary className="cursor-pointer list-none font-medium text-[var(--color-fg)]">
                              {acc.account}
                              <span className="ml-2 text-xs text-[var(--color-fg-subtle)]">
                                ({acc.positions.length} currencies)
                              </span>
                            </summary>
                            <ul className="mt-2 space-y-1 border-l border-[var(--color-border)] pl-3 text-xs text-[var(--color-fg-muted)]">
                              {acc.positions.map((p) => (
                                <li key={p.currency}>
                                  <Money>
                                    {p.amount.toLocaleString()} {p.currency}
                                  </Money>{' '}
                                  → <FormattedMoney value={p.value} currency={balances.currency} />
                                </li>
                              ))}
                            </ul>
                          </details>
                        </Td>
                        <Td align="right">
                          <FormattedMoney value={acc.value} currency={balances.currency} />
                        </Td>
                      </DataTableRow>
                    ))}
                  </tbody>
                </DataTable>
              </ChartShell>
            </div>
          )}
        </>
      )}

      {tab === 'files' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardTitle>Bank transaction files</CardTitle>
            <ul className="mt-4 space-y-2">
              {(files?.files ?? []).map((f) => (
                <li key={f.path}>
                  <button
                    type="button"
                    className={cn(
                      'w-full rounded-lg px-3 py-2 text-left text-sm transition-colors',
                      selectedFile === f.path
                        ? 'bg-[var(--color-accent-glow)] text-[var(--color-accent)]'
                        : 'hover:bg-[var(--color-surface-overlay)] text-[var(--color-fg)]'
                    )}
                    onClick={() => setSelectedFile(f.path)}
                  >
                    {f.name}
                    <span className="ml-2 text-[var(--color-fg-subtle)]">
                      {(f.size_bytes / 1024).toFixed(1)} KB
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {!files?.files?.length && (
              <p className="mt-4 text-sm text-[var(--color-fg-muted)]">No bank files found.</p>
            )}
          </Card>
          {selectedFile && fileContent && (
            <Card>
              <CardTitle>{fileContent.path.split('/').pop()}</CardTitle>
              <pre className="mt-4 max-h-[28rem] overflow-auto rounded-lg bg-[var(--color-surface)] p-4 font-mono text-xs text-[var(--color-fg-muted)]">
                {fileContent.content}
              </pre>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
