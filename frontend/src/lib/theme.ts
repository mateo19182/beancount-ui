export const CHART_PALETTE = [
  '#22d3ee',
  '#a78bfa',
  '#34d399',
  '#fb7185',
  '#fbbf24',
  '#60a5fa',
  '#f472b6',
  '#4ade80',
  '#c084fc',
  '#38bdf8',
] as const

export const CHART = {
  income: '#34d399',
  incomeDim: '#059669',
  expense: '#fb7185',
  expenseDim: '#e11d48',
  net: '#22d3ee',
  accent: '#2dd4bf',
  grid: '#1e2636',
  tooltipBg: '#1a2030',
  tooltipBorder: '#252d3d',
} as const

export function chartColor(index: number): string {
  return CHART_PALETTE[index % CHART_PALETTE.length]
}
