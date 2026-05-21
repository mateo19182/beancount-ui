import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMoney(value: number, currency: string) {
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 0 })} ${currency}`
}
