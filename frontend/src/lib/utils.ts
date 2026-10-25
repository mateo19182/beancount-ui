import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMoney(value: number, currency: string, compact = false) {
  if (compact && Math.abs(value) >= 1000) {
    return new Intl.NumberFormat(undefined, {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value) + ` ${currency}`
  }
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 0 })} ${currency}`
}

export function formatPercent(value: number, digits = 1) {
  return `${value.toFixed(digits)}%`
}

export function formatMonth(year: number, month: number) {
  const d = new Date(year, month - 1)
  return d.toLocaleString(undefined, { month: 'short', year: 'numeric' })
}

export function monthKey(year: number, month: number) {
  return `${year}-${String(month).padStart(2, '0')}`
}
