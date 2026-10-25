import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { chartColor } from '@/lib/theme'
import { formatMoney } from '@/lib/utils'
import { Money } from '@/lib/privacy-blur'
import { ChartTooltipContent } from './ChartTooltip'

interface Slice {
  name: string
  value: number
}

export function AllocationDonut({
  data,
  currency,
  centerLabel,
  centerValue,
  onSliceClick,
}: {
  data: Slice[]
  currency: string
  centerLabel?: string
  centerValue?: string
  onSliceClick?: (name: string) => void
}) {
  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div className="relative h-full w-full money-chart">
      {centerLabel && centerValue && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs text-[var(--color-fg-subtle)]">{centerLabel}</span>
          <span className="mt-0.5 text-lg font-bold tabular-nums text-[var(--color-fg)]">
            <Money>{centerValue}</Money>
          </span>
        </div>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
            stroke="none"
            onClick={(_, i) => {
              const name = data[i]?.name
              if (name && onSliceClick) onSliceClick(name)
            }}
            style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={chartColor(i)} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => (
              <ChartTooltipContent
                active={active}
                currency={currency}
                payload={payload?.map((p) => ({
                  name: String(p.name),
                  value: Number(p.value),
                  color: String(p.payload?.fill ?? p.color),
                }))}
              />
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      {total > 0 && (
        <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-1">
          {data.slice(0, 6).map((d, i) => (
            <button
              key={d.name}
              type="button"
              className="flex items-center gap-1.5 text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
              onClick={() => onSliceClick?.(d.name)}
            >
              <span className="h-2 w-2 rounded-full" style={{ background: chartColor(i) }} />
              {d.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function formatDonutCenter(value: number, currency: string) {
  return formatMoney(value, currency, true)
}
