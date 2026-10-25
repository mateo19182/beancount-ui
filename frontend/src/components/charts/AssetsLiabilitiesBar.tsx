import { Money } from '@/lib/privacy-blur'

export function BalanceStrip({
  assets,
  liabilities,
  netWorth,
  currency,
}: {
  assets: number
  liabilities: number
  netWorth: number
  currency: string
}) {
  const total = assets + Math.abs(liabilities)
  const assetPct = total > 0 ? (assets / total) * 100 : 50

  return (
    <div className="space-y-3">
      <div className="flex h-3 overflow-hidden rounded-full bg-[var(--color-surface)]">
        <div
          className="bg-gradient-to-r from-emerald-500 to-teal-400 transition-all"
          style={{ width: `${assetPct}%` }}
        />
        <div
          className="bg-gradient-to-r from-rose-500/80 to-rose-400/60 transition-all"
          style={{ width: `${100 - assetPct}%` }}
        />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <p className="text-[var(--color-fg-subtle)]">Assets</p>
          <p className="font-semibold tabular-nums text-[var(--color-income)]">
            <Money>{assets.toLocaleString()} {currency}</Money>
          </p>
        </div>
        <div>
          <p className="text-[var(--color-fg-subtle)]">Net</p>
          <p className="font-semibold tabular-nums text-[var(--color-accent)]">
            <Money>{netWorth.toLocaleString()} {currency}</Money>
          </p>
        </div>
        <div>
          <p className="text-[var(--color-fg-subtle)]">Liabilities</p>
          <p className="font-semibold tabular-nums text-[var(--color-expense)]">
            <Money>{liabilities.toLocaleString()} {currency}</Money>
          </p>
        </div>
      </div>
    </div>
  )
}
