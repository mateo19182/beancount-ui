import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '@/api/client'
import { Card, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function ChartsPage() {
  const navigate = useNavigate()
  const { data: monthsData } = useQuery({ queryKey: ['charts-months'], queryFn: api.chartsMonths })
  const months = monthsData?.months ?? []
  const latest = months[months.length - 1]
  const [year, setYear] = useState(latest?.year ?? new Date().getFullYear())
  const [month, setMonth] = useState(latest?.month ?? new Date().getMonth() + 1)

  const { data: ie } = useQuery({
    queryKey: ['charts-ie', year, month],
    queryFn: () => api.chartsIncomeExpenses(year, month),
  })
  const { data: expenses } = useQuery({
    queryKey: ['charts-exp', year, month],
    queryFn: () => api.chartsBreakdown(year, month, 'expenses'),
  })
  const { data: income } = useQuery({
    queryKey: ['charts-inc', year, month],
    queryFn: () => api.chartsBreakdown(year, month, 'income'),
  })

  const barData = useMemo(
    () =>
      ie
        ? [
            { name: 'Income', value: ie.income },
            { name: 'Expenses', value: ie.expenses },
          ]
        : [],
    [ie]
  )

  const monthStr = `${year}-${String(month).padStart(2, '0')}`

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Charts</h1>
      <div className="flex flex-wrap gap-2">
        {months.map((m) => (
          <Button
            key={`${m.year}-${m.month}`}
            variant={m.year === year && m.month === month ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setYear(m.year)
              setMonth(m.month)
            }}
          >
            {m.year}-{String(m.month).padStart(2, '0')}
          </Button>
        ))}
      </div>

      <Card>
        <CardTitle>Income vs Expenses ({year}-{month})</CardTitle>
        <div className="h-64 mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#1a73e8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <BreakdownCard
          title="Expenses"
          data={expenses?.categories ?? []}
          currency={expenses?.currency}
          onSelect={(name) =>
            navigate(`/transactions?month=${monthStr}&search=${encodeURIComponent(name)}`)
          }
        />
        <BreakdownCard
          title="Income"
          data={income?.categories ?? []}
          currency={income?.currency}
          onSelect={(name) =>
            navigate(`/transactions?month=${monthStr}&search=${encodeURIComponent(name)}`)
          }
        />
      </div>
    </div>
  )
}

function BreakdownCard({
  title,
  data,
  currency,
  onSelect,
}: {
  title: string
  data: { name: string; total: number }[]
  currency?: string
  onSelect: (name: string) => void
}) {
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      <div className="h-64 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis type="category" dataKey="name" width={120} />
            <Tooltip formatter={(v: number) => `${v.toLocaleString()} ${currency ?? ''}`} />
            <Bar
              dataKey="total"
              fill="#34a853"
              onClick={(row) => onSelect(row.name)}
              style={{ cursor: 'pointer' }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 text-sm">
        {data.map((c) => (
          <li key={c.name}>
            <button
              type="button"
              className="text-blue-600 hover:underline dark:text-blue-400"
              onClick={() => onSelect(c.name)}
            >
              {c.name}
            </button>
            {' — '}
            {c.total.toLocaleString()} {currency}
          </li>
        ))}
      </ul>
    </Card>
  )
}
