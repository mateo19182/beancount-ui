import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  type DateRange,
  formatRangeLabel,
  presetRange,
  type RangePresetId,
  yearRange,
} from '@/lib/dateRange'

const PRESETS: { id: RangePresetId; label: string }[] = [
  { id: 'month', label: 'Latest month' },
  { id: 'last-month', label: 'Last month' },
  { id: 'last-3-months', label: 'Last 3 months' },
  { id: 'ytd', label: 'YTD' },
  { id: 'last-year', label: 'Last year' },
  { id: 'all', label: 'All time' },
]

export function DateRangeFilter({
  range,
  onChange,
  months,
  activePreset,
  onPresetChange,
}: {
  range: DateRange
  onChange: (range: DateRange) => void
  months: { year: number; month: number }[]
  activePreset: RangePresetId | null
  onPresetChange: (id: RangePresetId | null) => void
}) {
  const years = [...new Set(months.map((m) => m.year))].sort((a, b) => b - a)

  const applyPreset = (id: RangePresetId, year?: number) => {
    const next = presetRange(id, months, year)
    if (next) {
      onChange(next)
      onPresetChange(id)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {PRESETS.map((p) => (
          <Button
            key={p.id}
            variant={activePreset === p.id ? 'default' : 'subtle'}
            size="sm"
            onClick={() => applyPreset(p.id)}
          >
            {p.label}
          </Button>
        ))}
        {years.map((y) => (
          <Button
            key={y}
            variant={activePreset === 'year' && range.from === yearRange(y).from ? 'default' : 'subtle'}
            size="sm"
            onClick={() => applyPreset('year', y)}
          >
            {y}
          </Button>
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs text-[var(--color-fg-muted)]">
          From
          <Input
            type="date"
            value={range.from}
            onChange={(e) => {
              onChange({ ...range, from: e.target.value })
              onPresetChange('custom')
            }}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-[var(--color-fg-muted)]">
          To
          <Input
            type="date"
            value={range.to}
            onChange={(e) => {
              onChange({ ...range, to: e.target.value })
              onPresetChange('custom')
            }}
          />
        </label>
        <p className="pb-2 text-sm text-[var(--color-fg-subtle)]">{formatRangeLabel(range)}</p>
      </div>
    </div>
  )
}
