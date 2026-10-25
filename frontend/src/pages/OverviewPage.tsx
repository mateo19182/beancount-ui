import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { api } from '@/api/client'
import { PageHeader } from '@/components/PageHeader'
import { LoadingState } from '@/components/LoadingState'
import { MetricCard } from '@/components/charts/MetricCard'
import { ChartShell } from '@/components/charts/ChartShell'
import { AllocationDonut, formatDonutCenter } from '@/components/charts/AllocationDonut'
import { BalanceStrip } from '@/components/charts/AssetsLiabilitiesBar'
import { DataTable, DataTableHead, DataTableRow, Th, Td } from '@/components/DataTable'
import { formatMoney, formatPercent } from '@/lib/utils'
import { FormattedMoney } from '@/lib/privacy-blur'
import { chartColor } from '@/lib/theme'

export function OverviewPage() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useQuery({ queryKey: ['overview'], queryFn: api.overview })

  if (isLoading) return <LoadingState />
  if (error) return <p className="text-[var(--color-expense)]">{String(error)}</p>
  if (!data) return null

  const chartData = data.categories.map((c) => ({ name: c.category, value: c.total }))
  const liabilityPct =
    data.total_assets > 0
      ? (Math.abs(data.total_liabilities) / data.total_assets) * 100
      : 0

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Your financial snapshot at a glance"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          label="Net worth"
          value={formatMoney(data.net_worth, data.currency)}
          accent="accent"
          onClick={() => navigate('/charts')}
        />
        <MetricCard
          label="Total assets"
          value={formatMoney(data.total_assets, data.currency)}
          accent="income"
          progress={100 - liabilityPct}
        />
        <MetricCard
          label="Liabilities"
          value={formatMoney(data.total_liabilities, data.currency)}
          accent="expense"
          progress={liabilityPct}
          sub={liabilityPct > 0 ? `${formatPercent(liabilityPct)} of assets` : undefined}
        />
      </div>

      <ChartShell title="Balance composition" subtitle="Assets vs liabilities" height="h-auto">
        <BalanceStrip
          assets={data.total_assets}
          liabilities={data.total_liabilities}
          netWorth={data.net_worth}
          currency={data.currency}
        />
      </ChartShell>

      <div className="grid gap-6 lg:grid-cols-5">
        <ChartShell
          title="Asset allocation"
          subtitle="Click a slice to filter transactions"
          className="lg:col-span-2"
        >
          <AllocationDonut
            data={chartData}
            currency={data.currency}
            centerLabel="Total assets"
            centerValue={formatDonutCenter(data.total_assets, data.currency)}
            onSliceClick={(cat) =>
              navigate(`/transactions?search=${encodeURIComponent(cat)}`)
            }
          />
        </ChartShell>

        <ChartShell title="By category" className="lg:col-span-3" height="h-auto">
          <DataTable>
            <DataTableHead>
              <Th>Category</Th>
              <Th align="right">Value</Th>
                <Th align="right">Share</Th>
                <th className="w-8 px-2 py-3" aria-hidden />
            </DataTableHead>
            <tbody>
              {data.categories.map((c, i) => (
                <DataTableRow
                  key={c.category}
                  onClick={() =>
                    navigate(`/transactions?search=${encodeURIComponent(c.category)}`)
                  }
                >
                  <Td>
                    <span className="flex items-center gap-2">
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: chartColor(i) }}
                      />
                      {c.category}
                    </span>
                  </Td>
                  <Td align="right">
                    <FormattedMoney value={c.total} currency={data.currency} />
                  </Td>
                  <Td align="right">
                    <span className="text-[var(--color-fg-muted)]">
                      {formatPercent(c.allocation_pct)}
                    </span>
                  </Td>
                  <Td align="right">
                    <ChevronRight className="inline h-4 w-4 text-[var(--color-fg-subtle)]" />
                  </Td>
                </DataTableRow>
              ))}
            </tbody>
          </DataTable>
        </ChartShell>
      </div>
    </div>
  )
}
