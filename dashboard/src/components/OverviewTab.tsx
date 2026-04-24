import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'

const COLORS = [
  '#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6b7280'
]

interface Props {
  insights: any
  categorySummary: any
}

function StatCard({ label, value, sub, color = 'emerald' }: {
  label: string; value: string; sub?: string; color?: string
}) {
  const colorMap: Record<string, string> = {
    emerald: 'border-emerald-500/30 bg-emerald-900/10',
    blue: 'border-blue-500/30 bg-blue-900/10',
    amber: 'border-amber-500/30 bg-amber-900/10',
    red: 'border-red-500/30 bg-red-900/10',
  }
  return (
    <div className={`rounded-xl border p-5 ${colorMap[color] || colorMap.emerald}`}>
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-2xl font-bold mt-1 text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

export function OverviewTab({ insights, categorySummary }: Props) {
  const categories = categorySummary?.categories ?? []
  const total = insights?.total_spending ?? 0
  const periodDays = categorySummary?.period_days ?? 30

  // Build pie chart data from top 8 categories
  const pieData = categories.slice(0, 8).map((c: any) => ({
    name: c.name,
    value: c.total,
  }))

  // Build bar chart data from top 10 categories
  const barData = categories.slice(0, 10).map((c: any) => ({
    name: c.name.length > 12 ? c.name.slice(0, 12) + '..' : c.name,
    amount: c.total,
    count: c.count,
  }))

  const topCategory = categories[0]
  const txCount = categories.reduce((sum: number, c: any) => sum + c.count, 0)
  const dailyAvg = total > 0 ? (total / periodDays).toFixed(2) : '0.00'

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label={`Total Spending (${periodDays}d)`}
          value={`$${total.toLocaleString('en-CA', { minimumFractionDigits: 2 })}`}
          sub="CAD"
          color="emerald"
        />
        <StatCard
          label="Daily Average"
          value={`$${dailyAvg}`}
          sub="per day"
          color="blue"
        />
        <StatCard
          label="Top Category"
          value={topCategory?.name ?? 'N/A'}
          sub={topCategory ? `$${topCategory.total.toFixed(2)}` : ''}
          color="amber"
        />
        <StatCard
          label="Transactions"
          value={txCount.toString()}
          sub={`${periodDays}-day period`}
          color="red"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-lg font-semibold mb-4">Spending Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={2}
                dataKey="value"
              >
                {pieData.map((_: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v: any) => [`$${Number(v).toFixed(2)}`, '']}
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-lg font-semibold mb-4">Category Totals</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData} layout="vertical" margin={{ left: 10 }}>
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis dataKey="name" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }} width={80} />
              <Tooltip
                formatter={(v: any) => [`$${Number(v).toFixed(2)}`, 'Amount']}
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
              />
              <Bar dataKey="amount" fill="#10b981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Insights Panel */}
      {insights?.ai_insights && (
        <div className="bg-gradient-to-br from-emerald-900/20 to-blue-900/20 border border-emerald-500/30 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-emerald-400 text-lg">✨</span>
            <h3 className="text-lg font-semibold text-emerald-300">AI Spending Insights</h3>
            <span className="ml-auto text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded-full">Claude-powered</span>
          </div>
          <p className="text-gray-300 leading-relaxed whitespace-pre-line">{insights.ai_insights}</p>
        </div>
      )}

      {/* Anomalies */}
      {insights?.anomalies?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-amber-400">⚠️</span> Spending Anomalies
          </h3>
          <div className="space-y-2">
            {insights.anomalies.map((a: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                <div>
                  <p className="font-medium capitalize">{a.merchant}</p>
                  <p className="text-xs text-gray-400">{a.category} • {a.date}</p>
                </div>
                <div className="text-right">
                  <p className="text-amber-400 font-semibold">${a.amount.toFixed(2)}</p>
                  <p className="text-xs text-gray-400">{a.multiplier}x normal</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
