import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { PositionsResponse } from '@/api/types'
import { Card, CardTitle } from '@/components/ui/card'
import { formatMoney } from '@/lib/utils'

export function CryptoPage() {
  const { data, isLoading, error } = useQuery<PositionsResponse>({
    queryKey: ['crypto'],
    queryFn: api.crypto,
  })

  if (isLoading) return <p>Loading...</p>
  if (error) return <p className="text-red-600">{String(error)}</p>
  if (!data) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Crypto</h1>
      <Card>
        <CardTitle>Total Value</CardTitle>
        <p className="mt-2 text-2xl font-bold">{formatMoney(data.total_value, data.currency)}</p>
      </Card>
      <Card>
        <CardTitle>Holdings</CardTitle>
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th>Symbol</th>
              <th>Amount</th>
              <th>Price</th>
              <th className="text-right">Value</th>
            </tr>
          </thead>
          <tbody>
            {data.positions.map((p) => (
              <tr key={p.symbol} className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2">{p.symbol}</td>
                <td>{p.amount ?? p.shares}</td>
                <td>{p.price?.toFixed(2) ?? '-'}</td>
                <td className="text-right">{p.value?.toLocaleString() ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
