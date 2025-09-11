import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
} from "recharts"

const scoreTrend = [
  { date: "Week 1", score: 58 },
  { date: "Week 2", score: 64 },
  { date: "Week 3", score: 71 },
  { date: "Week 4", score: 75 },
  { date: "Week 5", score: 81 },
  { date: "Week 6", score: 86 },
]

const categoryPerf = [
  { skill: "Algorithms", score: 80 },
  { skill: "Data Structures", score: 72 },
  { skill: "System Design", score: 67 },
  { skill: "Behavioral", score: 88 },
  { skill: "Debugging", score: 74 },
]

export default function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold">Analytics</h1>
      <p className="mt-1 text-sm text-foreground/70">Visualize performance and improvement over time.</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4" role="region" aria-label="Score trend over time">
          <h2 className="text-sm font-semibold">Score Trend</h2>
          <div className="mt-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={scoreTrend} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" stroke="currentColor" fontSize={12} />
                <YAxis domain={[0, 100]} stroke="currentColor" fontSize={12} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="score" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4" role="region" aria-label="Scores by category">
          <h2 className="text-sm font-semibold">Scores by Category</h2>
          <div className="mt-2 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryPerf} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="skill" stroke="currentColor" fontSize={12} />
                <YAxis domain={[0, 100]} stroke="currentColor" fontSize={12} />
                <Tooltip />
                <Legend />
                <Bar dataKey="score" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
