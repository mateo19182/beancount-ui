import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { PageHeader } from '@/components/PageHeader'
import { LoadingState } from '@/components/LoadingState'
import { DateRangeFilter } from '@/components/DateRangeFilter'
import { ChartShell } from '@/components/charts/ChartShell'
import { MetricCard } from '@/components/charts/MetricCard'
import {
  IncomeExpenseBar,
  CashflowTrend,
  NetSavingsArea,
} from '@/components/charts/IncomeExpenseCharts'
import { CategoryBreakdownChart } from '@/components/charts/CategoryBreakdownChart'
import { Badge } from '@/components/ui/badge'
import {
  type DateRange,
  formatRangeLabel,
  ledgerBounds,
  presetRange,
  type RangePresetId,
} from '@/lib/dateRange'
import { formatMoney } from '@/lib/utils'
import { FormattedMoney } from '@/lib/privacy-blur'

export function ChartsPage() {
  const navigate = useNavigate()
  const { data: monthsData, isLoading: monthsLoading } = useQuery({
    queryKey: ['charts-months'],
    queryFn: api.chartsMonths,
  })
  const months = monthsData?.months ?? []

  const [range, setRange] = useState<DateRange | null>(null)
  const [preset, setPreset] = useState<RangePresetId | null>('month')

  useEffect(() => {
    if (months.length > 0 && !range) {
      const initial = presetRange('month', months) ?? ledgerBounds(months)
      if (initial) setRange(initial)
    }
  }, [months, range])

  const from = range?.from ?? ''
  const to = range?.to ?? ''

  const { data: ie, isLoading: ieLoading } = useQuery({
    queryKey: ['charts-ie', from, to],
    queryFn: () => api.chartsIncomeExpenses(from, to),
    enabled: Boolean(from && to),
  })

  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['charts-trend', from, to],
    queryFn: () => api.chartsTrend(from, to),
    enabled: Boolean(from && to),
  })

  const { data: expenses } = useQuery({
    queryKey: ['charts-exp', from, to],
    queryFn: () => api.chartsBreakdown(from, to, 'expenses'),
    enabled: Boolean(from && to),
  })

  const { data: income } = useQuery({
    queryKey: ['charts-inc', from, to],
    queryFn: () => api.chartsBreakdown(from, to, 'income'),
    enabled: Boolean(from && to),
  })

  const trend = trendData?.months ?? []
  const net = ie ? ie.income - ie.expenses : 0
  const savingsRate = ie && ie.income > 0 ? ((ie.income - ie.expenses) / ie.income) * 100 : 0
  const rangeLabel = range ? formatRangeLabel(range) : ''
  const currency = ie?.currency ?? expenses?.currency ?? 'EUR'

  if (monthsLoading || !range) return <LoadingState />

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        description="Income, expenses, and category breakdowns over time"
      />

      <DateRangeFilter
        range={range}
        onChange={setRange}
        months={months}
        activePreset={preset}
        onPresetChange={setPreset}
      />

      {ie && !ieLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Income"
            value={formatMoney(ie.income, currency)}
            accent="income"
          />
          <MetricCard
            label="Expenses"
            value={formatMoney(ie.expenses, currency)}
            accent="expense"
          />
          <MetricCard
            label="Net"
            value={formatMoney(net, currency)}
            accent={net >= 0 ? 'accent' : 'expense'}
            sub={net >= 0 ? 'Saved in period' : 'Deficit in period'}
          />
          <MetricCard
            label="Savings rate"
            value={`${savingsRate.toFixed(1)}%`}
            accent={savingsRate >= 20 ? 'income' : savingsRate >= 0 ? 'default' : 'expense'}
            progress={Math.max(0, Math.min(100, savingsRate))}
          />
        </div>
      )}

      {trend.length > 1 && (
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartShell
            title="Cashflow trend"
            subtitle={`${rangeLabel} — income, expenses, net`}
            height="h-auto"
          >
            {trendLoading ? (
              <p className="text-sm text-[var(--color-fg-muted)]">Loading trend...</p>
            ) : (
              <CashflowTrend data={trend} currency={currency} />
            )}
          </ChartShell>
          <ChartShell title="Net savings" subtitle={`${rangeLabel} — monthly surplus or deficit`} height="h-auto">
            {trendLoading ? (
              <p className="text-sm text-[var(--color-fg-muted)]">Loading...</p>
            ) : (
              <NetSavingsArea data={trend} currency={currency} />
            )}
          </ChartShell>
        </div>
      )}

      {ie && (
        <ChartShell
          title={`${rangeLabel} overview`}
          subtitle="Income vs expenses vs net for selected period"
          height="h-auto"
        >
          <IncomeExpenseBar income={ie.income} expenses={ie.expenses} currency={currency} />
        </ChartShell>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <BreakdownPanel
          title="Expenses"
          kind="expense"
          data={expenses?.categories ?? []}
          currency={expenses?.currency}
          dateFrom={from}
          dateTo={to}
          onSelect={(search) =>
            navigate(
              `/transactions?date_from=${from}&date_to=${to}&search=${encodeURIComponent(search)}`
            )
          }
        />
        <BreakdownPanel
          title="Income"
          kind="income"
          data={income?.categories ?? []}
          currency={income?.currency}
          colorOffset={4}
          dateFrom={from}
          dateTo={to}
          onSelect={(search) =>
            navigate(
              `/transactions?date_from=${from}&date_to=${to}&search=${encodeURIComponent(search)}`
            )
          }
        />
      </div>
    </div>
  )
}

function BreakdownPanel({
  title,
  kind,
  data,
  currency,
  colorOffset = 0,
  dateFrom,
  dateTo,
  onSelect,
}: {
  title: string
  kind: 'income' | 'expense'
  data: {
    name: string
    total: number
    account?: string
    subcategories?: { name: string; total: number; account?: string }[]
  }[]
  currency?: string
  colorOffset?: number
  dateFrom: string
  dateTo: string
  onSelect: (search: string) => void
}) {
  const total = data.reduce((s, c) => s + c.total, 0)
  const subCount = data.reduce((s, c) => s + (c.subcategories?.length ?? 0), 0)

  return (
    <ChartShell
      title={title}
      subtitle={
        <>
          {data.length} categories · {subCount} subcategories ·{' '}
          <FormattedMoney value={total} currency={currency ?? ''} />
        </>
      }
      height="h-auto"
    >
      <CategoryBreakdownChart
        categories={data}
        currency={currency ?? ''}
        colorIndex={colorOffset}
        onSelect={onSelect}
      />
      <div className="mt-3">
        <Badge variant={kind === 'income' ? 'income' : 'expense'}>
          Click a bar to filter transactions ({dateFrom} – {dateTo})
        </Badge>
      </div>
    </ChartShell>
  )
}
