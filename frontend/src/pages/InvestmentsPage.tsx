import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { api } from '@/api/client'
import type { PositionsResponse } from '@/api/types'
import { PageHeader } from '@/components/PageHeader'
import { LoadingState } from '@/components/LoadingState'
import { EmptyState } from '@/components/EmptyState'
import { MetricCard } from '@/components/charts/MetricCard'
import { ChartShell } from '@/components/charts/ChartShell'
import { AllocationDonut } from '@/components/charts/AllocationDonut'
import { DataTable, DataTableHead, DataTableRow, Th, Td } from '@/components/DataTable'
import { ChartTooltipContent } from '@/components/charts/ChartTooltip'
import { formatMoney, formatPercent } from '@/lib/utils'
import { FormattedMoney, Money } from '@/lib/privacy-blur'
import { chartColor, CHART } from '@/lib/theme'

export function InvestmentsPage() {
  const { data, isLoading, error } = useQuery<PositionsResponse>({
    queryKey: ['investments'],
    queryFn: api.investments,
  })

  if (isLoading) return <LoadingState />
  if (error) return <p className="text-[var(--color-expense)]">{String(error)}</p>
  if (!data) return null

  const chartData = data.positions
    .filter((p) => p.value)
    .map((p) => ({ name: p.symbol, value: p.value! }))

  const topHolding = data.positions.reduce(
    (best, p) => (p.value && (!best || p.value > best.value) ? { symbol: p.symbol, value: p.value } : best),
    null as { symbol: string; value: number } | null
  )

  return (
    <div className="space-y-8">
      <PageHeader
        title="Investments"
        description="Stock and fund positions with allocation"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          label="Portfolio value"
          value={formatMoney(data.total_value, data.currency)}
          accent="accent"
        />
        <MetricCard
          label="Holdings"
          value={String(data.positions.length)}
          sub="Active positions"
        />
        {topHolding && (
          <MetricCard
            label="Largest position"
            value={topHolding.symbol}
            sub={formatMoney(topHolding.value, data.currency)}
            accent="income"
          />
        )}
      </div>

      {data.positions.length === 0 ? (
        <EmptyState title="No investment positions" description="Add stock accounts to your ledger" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          {chartData.length > 0 && (
            <ChartShell title="Allocation" className="lg:col-span-2">
              <AllocationDonut
                data={chartData}
                currency={data.currency}
                centerLabel="Total"
                centerValue={formatMoney(data.total_value, data.currency, true)}
              />
            </ChartShell>
          )}

          {chartData.length > 0 && (
            <ChartShell title="By value" className="lg:col-span-3" height="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ bottom: 32, left: 8, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: 'var(--color-fg-muted)', fontSize: 10 }}
                    angle={-30}
                    textAnchor="end"
                    height={48}
                  />
                  <YAxis tick={{ fill: 'var(--color-fg-muted)', fontSize: 11 }} />
                  <Tooltip
                    content={({ active, payload }) => (
                      <ChartTooltipContent
                        active={active}
                        currency={data.currency}
                        payload={payload?.map((p) => ({
                          name: String(p.payload?.name),
                          value: Number(p.value),
                        }))}
                      />
                    )}
                  />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={chartColor(i)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartShell>
          )}

          <ChartShell title="Holdings detail" className="lg:col-span-5" height="h-auto">
            <DataTable>
              <DataTableHead>
                <Th>Symbol</Th>
                <Th>Account</Th>
                <Th align="right">Shares</Th>
                <Th align="right">Price</Th>
                <Th align="right">Value</Th>
                <Th align="right">Weight</Th>
              </DataTableHead>
              <tbody>
                {data.positions.map((p, i) => {
                  const weight =
                    data.total_value > 0 && p.value
                      ? (p.value / data.total_value) * 100
                      : 0
                  return (
                    <DataTableRow key={`${p.symbol}-${p.account}`}>
                      <Td>
                        <span className="flex items-center gap-2 font-medium">
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{ background: chartColor(i) }}
                          />
                          {p.symbol}
                        </span>
                      </Td>
                      <Td className="text-[var(--color-fg-muted)]">{p.account ?? '—'}</Td>
                      <Td align="right">{p.shares?.toLocaleString() ?? '—'}</Td>
                      <Td align="right">
                        {p.price != null ? <Money>{p.price.toFixed(2)}</Money> : '—'}
                      </Td>
                      <Td align="right">
                        {p.value ? <FormattedMoney value={p.value} currency={data.currency} /> : '—'}
                      </Td>
                      <Td align="right">
                        <span className="text-[var(--color-fg-muted)]">
                          {weight > 0 ? formatPercent(weight) : '—'}
                        </span>
                      </Td>
                    </DataTableRow>
                  )
                })}
              </tbody>
            </DataTable>
          </ChartShell>
        </div>
      )}
    </div>
  )
}
