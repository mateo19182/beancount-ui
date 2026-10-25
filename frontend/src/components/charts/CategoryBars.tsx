import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'
import { chartColor, CHART } from '@/lib/theme'
import { ChartTooltipContent } from './ChartTooltip'

interface CategoryItem {
  name: string
  total: number
}

export function CategoryBars({
  data,
  currency,
  colorIndex = 0,
  layout = 'vertical',
  onSelect,
}: {
  data: CategoryItem[]
  currency: string
  colorIndex?: number
  layout?: 'vertical' | 'horizontal'
  onSelect?: (name: string) => void
}) {
  const sorted = [...data].sort((a, b) => b.total - a.total).slice(0, 12)
  const isVertical = layout === 'vertical'

  const chartHeight = Math.max(200, sorted.length * 28)

  return (
    <div className="w-full money-chart" style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={sorted}
        layout={isVertical ? 'vertical' : 'horizontal'}
        margin={isVertical ? { left: 4, right: 16, top: 8, bottom: 8 } : { bottom: 48, left: 8, right: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={!isVertical} vertical={isVertical} />
        {isVertical ? (
          <>
            <XAxis type="number" tick={{ fill: '#8b95a8', fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="name"
              width={120}
              tick={{ fill: '#8b95a8', fontSize: 11 }}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey="name"
              angle={-35}
              textAnchor="end"
              height={70}
              tick={{ fill: '#8b95a8', fontSize: 10 }}
            />
            <YAxis tick={{ fill: '#8b95a8', fontSize: 11 }} />
          </>
        )}
        <Tooltip
          cursor={{ fill: 'rgba(45, 212, 191, 0.06)' }}
          content={({ active, payload, label }) => (
            <ChartTooltipContent
              active={active}
              label={label}
              currency={currency}
              payload={payload?.map((p) => ({
                name: String(p.payload?.name ?? p.name),
                value: Number(p.value),
              }))}
            />
          )}
        />
        <Bar
          dataKey="total"
          radius={isVertical ? [0, 4, 4, 0] : [4, 4, 0, 0]}
          onClick={(row) => onSelect?.(row.name)}
          style={{ cursor: onSelect ? 'pointer' : 'default' }}
        >
          {sorted.map((_, i) => (
            <Cell key={i} fill={chartColor(colorIndex + i)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
    </div>
  )
}
