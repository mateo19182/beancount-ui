import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '@/api/client'
import type { PositionsResponse } from '@/api/types'
import { Card, CardTitle } from '@/components/ui/card'
import { formatMoney } from '@/lib/utils'

export function InvestmentsPage() {
  const { data, isLoading, error } = useQuery<PositionsResponse>({
    queryKey: ['investments'],
    queryFn: api.investments,
  })

  if (isLoading) return <p>Loading...</p>
  if (error) return <p className="text-red-600">{String(error)}</p>
  if (!data) return null

  const chartData = data.positions
    .filter((p) => p.value)
    .map((p) => ({ name: p.symbol, value: p.value! }))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Investments</h1>
      <Card>
        <CardTitle>Total Value</CardTitle>
        <p className="mt-2 text-2xl font-bold">{formatMoney(data.total_value, data.currency)}</p>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>Holdings</CardTitle>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Symbol</th>
                <th>Shares</th>
                <th>Price</th>
                <th className="text-right">Value</th>
              </tr>
            </thead>
            <tbody>
              {data.positions.map((p) => (
                <tr key={`${p.symbol}-${p.account}`} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-2">{p.symbol}</td>
                  <td>{p.shares}</td>
                  <td>{p.price?.toFixed(2) ?? '-'}</td>
                  <td className="text-right">{p.value?.toLocaleString() ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        {chartData.length > 0 && (
          <Card>
            <CardTitle>Allocation</CardTitle>
            <div className="h-72 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#1a73e8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
