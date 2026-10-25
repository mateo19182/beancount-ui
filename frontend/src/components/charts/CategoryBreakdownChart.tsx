import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ChartBreakdownCategory } from '@/api/types'
import { chartColor, CHART } from '@/lib/theme'
import { ChartTooltipContent } from './ChartTooltip'

export interface BreakdownBarRow {
  name: string
  total: number
  search: string
  group: string
}

export function flattenBreakdown(
  categories: ChartBreakdownCategory[],
): BreakdownBarRow[] {
  const rows: BreakdownBarRow[] = []

  for (const cat of categories) {
    const subs = cat.subcategories ?? []
    if (subs.length === 0) {
      rows.push({
        name: cat.name,
        total: cat.total,
        search: cat.account ?? cat.name,
        group: cat.name,
      })
      continue
    }
    for (const sub of subs) {
      rows.push({
        name: `${cat.name} › ${sub.name}`,
        total: sub.total,
        search: sub.account ?? `${cat.name}:${sub.name}`,
        group: cat.name,
      })
    }
  }

  return rows.sort((a, b) => b.total - a.total).slice(0, 24)
}

export function CategoryBreakdownChart({
  categories,
  currency,
  colorIndex = 0,
  onSelect,
}: {
  categories: ChartBreakdownCategory[]
  currency: string
  colorIndex?: number
  onSelect?: (search: string) => void
}) {
  const rows = flattenBreakdown(categories)
  const groups = [...new Set(rows.map((r) => r.group))]
  const groupColor = new Map(
    groups.map((g, i) => [g, chartColor(colorIndex + i)]),
  )

  if (rows.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-[var(--color-fg-muted)]">
        No transactions in this period
      </p>
    )
  }

  const chartHeight = Math.max(220, rows.length * 32)

  return (
    <div className="w-full money-chart" style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ left: 4, right: 20, top: 8, bottom: 8 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={CHART.grid}
            horizontal={false}
          />
          <XAxis
            type="number"
            tick={{ fill: '#8b95a8', fontSize: 11 }}
            domain={[0, 'auto']}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={148}
            tick={{ fill: '#8b95a8', fontSize: 11 }}
          />
          <Tooltip
            cursor={{ fill: 'rgba(45, 212, 191, 0.06)' }}
            content={({ active, payload }) => {
              const row = payload?.[0]?.payload as BreakdownBarRow | undefined
              return (
                <ChartTooltipContent
                  active={active}
                  label={row?.name}
                  currency={currency}
                  payload={
                    row
                      ? [{ name: row.name, value: row.total, color: groupColor.get(row.group) }]
                      : undefined
                  }
                />
              )
            }}
          />
          <Bar
            dataKey="total"
            radius={[0, 4, 4, 0]}
            onClick={(row: BreakdownBarRow) => onSelect?.(row.search)}
            style={{ cursor: onSelect ? 'pointer' : 'default' }}
          >
            {rows.map((row) => (
              <Cell key={row.search} fill={groupColor.get(row.group)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
