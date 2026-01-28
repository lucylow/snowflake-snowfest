"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, Calendar } from "lucide-react"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Line, LineChart, XAxis, YAxis, ResponsiveContainer, Legend } from "recharts"

interface JobWithDate {
  jobId: string
  jobName: string
  createdAt: string
  best_score?: number
  results?: Array<{
    modes?: Array<{
      affinity: number
    }>
  }>
}

interface TrendAnalysisProps {
  jobs: JobWithDate[]
}

export function TrendAnalysis({ jobs }: TrendAnalysisProps) {
  // Sort jobs by date
  const sortedJobs = [...jobs]
    .filter((j) => j.createdAt)
    .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())

  if (sortedJobs.length < 2) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trend Analysis</CardTitle>
          <CardDescription>Need at least 2 jobs with dates to analyze trends</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  // Process data for trend analysis
  const trendData = sortedJobs.map((job) => {
    let meanScore: number | undefined
    let bestScore = job.best_score

    if (!bestScore && job.results) {
      const allAffinities: number[] = []
      job.results.forEach((result) => {
        const modes = result.modes || []
        const affinities = modes.map((m) => m.affinity).filter((a): a is number => a !== undefined)
        allAffinities.push(...affinities)
      })

      if (allAffinities.length > 0) {
        bestScore = Math.min(...allAffinities)
        meanScore = allAffinities.reduce((a, b) => a + b, 0) / allAffinities.length
      }
    }

    return {
      date: new Date(job.createdAt).toLocaleDateString(),
      timestamp: new Date(job.createdAt).getTime(),
      jobName: job.jobName,
      best_score: bestScore,
      mean_score: meanScore,
    }
  }).filter((d) => d.best_score !== undefined)

  // Calculate trend metrics
  const firstScore = trendData[0]?.best_score
  const lastScore = trendData[trendData.length - 1]?.best_score
  const trend = firstScore && lastScore ? lastScore - firstScore : 0
  const isImproving = trend < 0 // Lower (more negative) is better

  // Calculate moving average (3-point)
  const movingAverage = trendData.map((_, idx) => {
    if (idx < 2) return null
    const window = trendData.slice(idx - 2, idx + 1)
    const scores = window.map((d) => d.best_score).filter((s): s is number => s !== undefined)
    return scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null
  })

  const chartData = trendData.map((d, idx) => ({
    ...d,
    moving_avg: movingAverage[idx] || null,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          Trend Analysis
        </CardTitle>
        <CardDescription>Track performance metrics over time</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Trend Summary */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 bg-muted rounded-lg">
            <div className="text-xs text-muted-foreground mb-1">Jobs Analyzed</div>
            <div className="text-2xl font-bold">{trendData.length}</div>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <div className="text-xs text-muted-foreground mb-1">Trend</div>
            <div className={`text-2xl font-bold flex items-center gap-2 ${isImproving ? "text-green-600" : "text-red-600"}`}>
              {isImproving ? "↓ Improving" : "↑ Declining"}
              <span className="text-sm">({Math.abs(trend).toFixed(2)} kcal/mol)</span>
            </div>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <div className="text-xs text-muted-foreground mb-1">Latest Score</div>
            <div className="text-2xl font-bold">{lastScore?.toFixed(2) || "N/A"}</div>
            <div className="text-xs text-muted-foreground">kcal/mol</div>
          </div>
        </div>

        {/* Trend Chart */}
        <div>
          <h4 className="font-semibold mb-4">Performance Over Time</h4>
          <ChartContainer
            config={{
              best_score: {
                label: "Best Score",
                color: "hsl(var(--chart-1))",
              },
              mean_score: {
                label: "Mean Score",
                color: "hsl(var(--chart-2))",
              },
              moving_avg: {
                label: "Moving Average (3pt)",
                color: "hsl(var(--chart-3))",
              },
            }}
            className="h-[350px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} fontSize={10} />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="best_score"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  name="Best Score"
                />
                {chartData.some((d) => d.mean_score !== undefined) && (
                  <Line
                    type="monotone"
                    dataKey="mean_score"
                    stroke="hsl(var(--chart-2))"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={{ r: 3 }}
                    name="Mean Score"
                  />
                )}
                {chartData.some((d) => d.moving_avg !== null) && (
                  <Line
                    type="monotone"
                    dataKey="moving_avg"
                    stroke="hsl(var(--chart-3))"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    dot={false}
                    name="Moving Avg"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>

        {/* Period Analysis */}
        <div>
          <h4 className="font-semibold mb-4">Period Comparison</h4>
          <div className="grid grid-cols-2 gap-4">
            {trendData.length >= 4 && (() => {
              const midpoint = Math.floor(trendData.length / 2)
              const firstHalf = trendData.slice(0, midpoint)
              const secondHalf = trendData.slice(midpoint)

              const firstHalfAvg = firstHalf.reduce((sum, d) => sum + (d.best_score || 0), 0) / firstHalf.length
              const secondHalfAvg = secondHalf.reduce((sum, d) => sum + (d.best_score || 0), 0) / secondHalf.length

              return (
                <>
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-xs text-muted-foreground mb-1">First Half Average</div>
                    <div className="text-xl font-bold">{firstHalfAvg.toFixed(2)}</div>
                    <div className="text-xs text-muted-foreground">kcal/mol</div>
                  </div>
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-xs text-muted-foreground mb-1">Second Half Average</div>
                    <div className="text-xl font-bold">{secondHalfAvg.toFixed(2)}</div>
                    <div className="text-xs text-muted-foreground">kcal/mol</div>
                    <div className={`text-xs mt-1 ${secondHalfAvg < firstHalfAvg ? "text-green-600" : "text-red-600"}`}>
                      {secondHalfAvg < firstHalfAvg ? "↓ Improved" : "↑ Declined"} by{" "}
                      {Math.abs(secondHalfAvg - firstHalfAvg).toFixed(2)}
                    </div>
                  </div>
                </>
              )
            })()}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
