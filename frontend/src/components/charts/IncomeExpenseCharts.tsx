import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  CartesianGrid,
  Tooltip,
  Legend,
  Line,
  ComposedChart,
  ReferenceLine,
  Area,
  AreaChart,
  Cell,
} from 'recharts'
import { CHART } from '@/lib/theme'
import { formatMoney, formatMonth } from '@/lib/utils'
import { ChartTooltipContent } from './ChartTooltip'

const TICK = { fill: '#8b95a8', fontSize: 11 }
const TICK_SM = { fill: '#8b95a8', fontSize: 10 }

function ChartPlot({
  children,
  height = 280,
}: {
  children: React.ReactElement
  height?: number
}) {
  return (
    <div className="w-full money-chart" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  )
}

export function IncomeExpenseBar({
  income,
  expenses,
  currency,
}: {
  income: number
  expenses: number
  currency: string
}) {
  const data = [
    { name: 'Income', value: income, fill: CHART.income },
    { name: 'Expenses', value: expenses, fill: CHART.expense },
  ]

  return (
    <ChartPlot height={240}>
      <BarChart data={data} margin={{ top: 16, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="name" tick={TICK} />
        <YAxis tick={TICK} domain={[0, 'auto']} />
        <Tooltip
          content={({ active, payload }) => (
            <ChartTooltipContent
              active={active}
              currency={currency}
              payload={payload?.map((p) => ({
                name: String(p.payload?.name),
                value: Number(p.value),
                color: String(p.payload?.fill),
              }))}
            />
          )}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartPlot>
  )
}

export interface MonthlyTrendPoint {
  year: number
  month: number
  income: number
  expenses: number
}

export function CashflowTrend({ data, currency }: { data: MonthlyTrendPoint[]; currency: string }) {
  const chartData = data.map((d) => ({
    label: formatMonth(d.year, d.month),
    income: d.income,
    expenses: d.expenses,
    net: d.income - d.expenses,
  }))
  const crowded = chartData.length > 6
  const height = Math.max(280, chartData.length * 32)

  return (
    <ChartPlot height={height}>
      <ComposedChart
        data={chartData}
        margin={{ top: 8, right: 8, left: 4, bottom: crowded ? 48 : 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis
          dataKey="label"
          tick={TICK_SM}
          angle={crowded ? -35 : 0}
          textAnchor={crowded ? 'end' : 'middle'}
          height={crowded ? 56 : 30}
          interval={0}
        />
        <YAxis tick={TICK} width={56} />
        <Tooltip
          content={({ active, payload, label }) => (
            <ChartTooltipContent
              active={active}
              label={label}
              currency={currency}
              payload={payload?.map((p) => ({
                name: String(p.name),
                value: Number(p.value),
                color: p.color,
              }))}
            />
          )}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#8b95a8' }} />
        <Bar
          dataKey="income"
          fill={CHART.income}
          radius={[4, 4, 0, 0]}
          barSize={crowded ? 10 : 16}
          name="Income"
        />
        <Bar
          dataKey="expenses"
          fill={CHART.expense}
          radius={[4, 4, 0, 0]}
          barSize={crowded ? 10 : 16}
          name="Expenses"
        />
        <Line
          type="monotone"
          dataKey="net"
          stroke={CHART.net}
          strokeWidth={2}
          dot={{ fill: CHART.net, r: 3 }}
          name="Net"
        />
      </ComposedChart>
    </ChartPlot>
  )
}

export function NetSavingsArea({ data, currency }: { data: MonthlyTrendPoint[]; currency: string }) {
  const chartData = data.map((d) => ({
    label: formatMonth(d.year, d.month),
    net: d.income - d.expenses,
  }))
  const crowded = chartData.length > 6
  const height = Math.max(280, chartData.length * 32)

  return (
    <ChartPlot height={height}>
      <AreaChart
        data={chartData}
        margin={{ top: 8, right: 8, left: 4, bottom: crowded ? 48 : 8 }}
      >
        <defs>
          <linearGradient id="netArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART.net} stopOpacity={0.35} />
            <stop offset="100%" stopColor={CHART.net} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis
          dataKey="label"
          tick={TICK_SM}
          angle={crowded ? -35 : 0}
          textAnchor={crowded ? 'end' : 'middle'}
          height={crowded ? 56 : 30}
          interval={0}
        />
        <YAxis tick={TICK} width={56} />
        <ReferenceLine y={0} stroke={CHART.grid} strokeDasharray="4 4" />
        <Tooltip
          formatter={(v: number) => formatMoney(v, currency)}
          labelStyle={{ color: '#e8ecf4' }}
          contentStyle={{
            background: CHART.tooltipBg,
            border: `1px solid ${CHART.tooltipBorder}`,
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          type="monotone"
          dataKey="net"
          stroke={CHART.net}
          fill="url(#netArea)"
          strokeWidth={2}
          name="Net savings"
        />
      </AreaChart>
    </ChartPlot>
  )
}
