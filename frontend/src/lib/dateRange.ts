export interface DateRange {
  from: string
  to: string
}

export function lastDayOfMonth(year: number, month: number): string {
  const d = new Date(year, month, 0)
  return isoDate(d)
}

export function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function monthRange(year: number, month: number): DateRange {
  return {
    from: `${year}-${String(month).padStart(2, '0')}-01`,
    to: lastDayOfMonth(year, month),
  }
}

export function yearRange(year: number): DateRange {
  return { from: `${year}-01-01`, to: `${year}-12-31` }
}

export function ytdRange(year = new Date().getFullYear()): DateRange {
  return { from: `${year}-01-01`, to: isoDate(new Date()) }
}

export function rollingMonthsRange(
  anchor: { year: number; month: number },
  count: number
): DateRange {
  const end = monthRange(anchor.year, anchor.month)
  const startDate = new Date(anchor.year, anchor.month - count, 1)
  return { from: isoDate(startDate), to: end.to }
}

export function formatRangeLabel(range: DateRange): string {
  const from = parseIso(range.from)
  const to = parseIso(range.to)
  if (
    from.getDate() === 1 &&
    range.to === lastDayOfMonth(from.getFullYear(), from.getMonth() + 1) &&
    from.getMonth() === to.getMonth() &&
    from.getFullYear() === to.getFullYear()
  ) {
    return from.toLocaleString(undefined, { month: 'long', year: 'numeric' })
  }
  if (
    from.getMonth() === 0 &&
    from.getDate() === 1 &&
    to.getMonth() === 11 &&
    to.getDate() === 31 &&
    from.getFullYear() === to.getFullYear()
  ) {
    return String(from.getFullYear())
  }
  const sameYear = from.getFullYear() === to.getFullYear()
  const fmt: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  if (!sameYear) fmt.year = 'numeric'
  const toFmt: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' }
  return `${from.toLocaleDateString(undefined, fmt)} – ${to.toLocaleDateString(undefined, toFmt)}`
}

function parseIso(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function ledgerBounds(months: { year: number; month: number }[]): DateRange | null {
  if (months.length === 0) return null
  const first = months[0]
  const last = months[months.length - 1]
  return {
    from: monthRange(first.year, first.month).from,
    to: monthRange(last.year, last.month).to,
  }
}

export type RangePresetId =
  | 'month'
  | 'last-month'
  | 'last-3-months'
  | 'ytd'
  | 'year'
  | 'last-year'
  | 'all'
  | 'custom'

export function presetRange(
  id: RangePresetId,
  months: { year: number; month: number }[],
  year?: number
): DateRange | null {
  const latest = months[months.length - 1]
  if (!latest && id !== 'custom') return null
  const now = new Date()
  const cy = now.getFullYear()

  switch (id) {
    case 'month':
      return monthRange(latest.year, latest.month)
    case 'last-month': {
      const d = new Date(latest.year, latest.month - 2, 1)
      return monthRange(d.getFullYear(), d.getMonth() + 1)
    }
    case 'last-3-months':
      return rollingMonthsRange(latest, 3)
    case 'ytd':
      return ytdRange(cy)
    case 'year':
      return yearRange(year ?? latest.year)
    case 'last-year':
      return yearRange(cy - 1)
    case 'all':
      return ledgerBounds(months)
    default:
      return null
  }
}
