import { formatMoney } from '@/lib/utils'
import { Money } from '@/lib/privacy-blur'
import { CHART } from '@/lib/theme'

export function ChartTooltipContent({
  active,
  payload,
  label,
  currency,
}: {
  active?: boolean
  payload?: { name: string; value: number; color?: string }[]
  label?: string
  currency?: string
}) {
  if (!active || !payload?.length) return null

  return (
    <div
      className="rounded-lg border px-3 py-2 text-xs shadow-xl"
      style={{
        background: CHART.tooltipBg,
        borderColor: CHART.tooltipBorder,
      }}
    >
      {label && <p className="mb-1.5 font-medium text-[var(--color-fg)]">{label}</p>}
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center justify-between gap-6">
          <span className="flex items-center gap-1.5 text-[var(--color-fg-muted)]">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: entry.color ?? CHART.accent }}
            />
            {entry.name}
          </span>
          <span className="font-semibold tabular-nums text-[var(--color-fg)]">
            <Money>
              {currency ? formatMoney(entry.value, currency) : entry.value.toLocaleString()}
            </Money>
          </span>
        </div>
      ))}
    </div>
  )
}
