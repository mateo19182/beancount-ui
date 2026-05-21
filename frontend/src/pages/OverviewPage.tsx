import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { api } from '@/api/client'
import { Card, CardTitle } from '@/components/ui/card'
import { formatMoney } from '@/lib/utils'

const COLORS = ['#1a73e8', '#34a853', '#fbbc04', '#ea4335', '#9c27b0', '#00bcd4']

export function OverviewPage() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useQuery({ queryKey: ['overview'], queryFn: api.overview })

  if (isLoading) return <p>Loading...</p>
  if (error) return <p className="text-red-600">{String(error)}</p>
  if (!data) return null

  const chartData = data.categories.map((c) => ({ name: c.category, value: c.total }))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Overview</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardTitle>Net Worth</CardTitle>
          <p className="mt-2 text-2xl font-bold">{formatMoney(data.net_worth, data.currency)}</p>
        </Card>
        <Card>
          <CardTitle>Assets</CardTitle>
          <p className="mt-2 text-2xl">{formatMoney(data.total_assets, data.currency)}</p>
        </Card>
        <Card>
          <CardTitle>Liabilities</CardTitle>
          <p className="mt-2 text-2xl">{formatMoney(data.total_liabilities, data.currency)}</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle>Assets by Category</CardTitle>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th>Category</th>
                <th className="text-right">Value</th>
                <th className="text-right">%</th>
              </tr>
            </thead>
            <tbody>
              {data.categories.map((c) => (
                <tr
                  key={c.category}
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900"
                  onClick={() => navigate(`/transactions?search=${encodeURIComponent(c.category)}`)}
                >
                  <td className="py-2">{c.category}</td>
                  <td className="py-2 text-right">{formatMoney(c.total, data.currency)}</td>
                  <td className="py-2 text-right">{c.allocation_pct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card>
          <CardTitle>Allocation</CardTitle>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label
                  onClick={(_, index) => {
                    const cat = chartData[index]?.name
                    if (cat) navigate(`/transactions?search=${encodeURIComponent(cat)}`)
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatMoney(v, data.currency)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}
