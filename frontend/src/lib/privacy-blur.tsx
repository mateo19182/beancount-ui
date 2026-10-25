import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { formatMoney } from '@/lib/utils'
import { cn } from '@/lib/utils'

const STORAGE_KEY = 'beancount-ui-blur-amounts'

type PrivacyBlurContextValue = {
  blurAmounts: boolean
  toggleBlurAmounts: () => void
}

const PrivacyBlurContext = createContext<PrivacyBlurContextValue | null>(null)

function readStoredBlur(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function PrivacyBlurProvider({ children }: { children: ReactNode }) {
  const [blurAmounts, setBlurAmounts] = useState(readStoredBlur)

  useEffect(() => {
    document.documentElement.toggleAttribute('data-blur-amounts', blurAmounts)
  }, [blurAmounts])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, blurAmounts ? '1' : '0')
    } catch {
      // ignore storage errors
    }
  }, [blurAmounts])

  const toggleBlurAmounts = useCallback(() => {
    setBlurAmounts((prev) => !prev)
  }, [])

  const value = useMemo(
    () => ({ blurAmounts, toggleBlurAmounts }),
    [blurAmounts, toggleBlurAmounts]
  )

  return <PrivacyBlurContext.Provider value={value}>{children}</PrivacyBlurContext.Provider>
}

export function usePrivacyBlur() {
  const ctx = useContext(PrivacyBlurContext)
  if (!ctx) {
    throw new Error('usePrivacyBlur must be used within PrivacyBlurProvider')
  }
  return ctx
}

export function Money({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <span className={cn('money-value', className)}>{children}</span>
}

export function FormattedMoney({
  value,
  currency,
  compact,
  className,
}: {
  value: number
  currency: string
  compact?: boolean
  className?: string
}) {
  return (
    <Money className={className}>
      {formatMoney(value, currency, compact)}
    </Money>
  )
}
