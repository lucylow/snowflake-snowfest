"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { GitCompare, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, XAxis, YAxis, ResponsiveContainer, LineChart, Line, Legend } from "recharts"

interface JobResult {
  jobId: string
  jobName: string
  results?: Array<{
    ligand_name: string
    modes?: Array<{
      affinity: number
    }>
  }>
  best_score?: number
}

interface ComparativeAnalysisProps {
  jobs: JobResult[]
}

export function ComparativeAnalysis({ jobs }: ComparativeAnalysisProps) {
  const [selectedJobs, setSelectedJobs] = useState<string[]>(jobs.slice(0, 3).map((j) => j.jobId))

  if (jobs.length < 2) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Comparative Analysis</CardTitle>
          <CardDescription>Need at least 2 jobs to compare</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  // Process selected jobs
  const selectedJobData = jobs.filter((j) => selectedJobs.includes(j.jobId))

  const comparisonData = selectedJobData.map((job) => {
    const allAffinities: number[] = []
    job.results?.forEach((result) => {
      const modes = result.modes || []
      const affinities = modes.map((m) => m.affinity).filter((a): a is number => a !== undefined)
      allAffinities.push(...affinities)
    })

    if (allAffinities.length === 0) return null

    const sorted = [...allAffinities].sort((a, b) => a - b)
    const mean = allAffinities.reduce((a, b) => a + b, 0) / allAffinities.length
    const median = sorted[Math.floor(sorted.length / 2)]
    const min = Math.min(...allAffinities)
    const max = Math.max(...allAffinities)

    return {
      jobId: job.jobId,
      jobName: job.jobName,
      count: allAffinities.length,
      mean,
      median,
      min,
      max,
      best_score: job.best_score || min,
    }
  }).filter((d): d is NonNullable<typeof d> => d !== null)

  // Calculate differences
  const bestJob = comparisonData.reduce((best, current) =>
    current.best_score < best.best_score ? current : best,
    comparisonData[0]
  )

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="w-5 h-5" />
              Comparative Analysis
            </CardTitle>
            <CardDescription>Compare statistical metrics across multiple jobs</CardDescription>
          </div>
          <Select
            value={selectedJobs.join(",")}
            onValueChange={(value) => setSelectedJobs(value.split(","))}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select jobs" />
            </SelectTrigger>
            <SelectContent>
              {jobs.map((job) => (
                <SelectItem key={job.jobId} value={job.jobId}>
                  {job.jobName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Best Job Highlight */}
        {bestJob && (
          <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">Best Performing Job</div>
                <div className="text-lg font-semibold">{bestJob.jobName}</div>
              </div>
              <Badge variant="default" className="gap-2">
                <TrendingDown className="w-3 h-3" />
                {bestJob.best_score.toFixed(2)} kcal/mol
              </Badge>
            </div>
          </div>
        )}

        {/* Comparison Chart */}
        <div>
          <h4 className="font-semibold mb-4">Statistical Comparison</h4>
          <ChartContainer
            config={{
              mean: {
                label: "Mean Score",
                color: "hsl(var(--chart-1))",
              },
              median: {
                label: "Median Score",
                color: "hsl(var(--chart-2))",
              },
              best_score: {
                label: "Best Score",
                color: "hsl(var(--chart-3))",
              },
            }}
            className="h-[300px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData}>
                <XAxis dataKey="jobName" angle={-45} textAnchor="end" height={80} fontSize={10} />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Legend />
                <Bar dataKey="mean" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="median" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="best_score" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>

        {/* Detailed Comparison Table */}
        <div>
          <h4 className="font-semibold mb-4">Detailed Metrics</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Job</th>
                  <th className="text-right p-2">Count</th>
                  <th className="text-right p-2">Mean</th>
                  <th className="text-right p-2">Median</th>
                  <th className="text-right p-2">Best</th>
                  <th className="text-right p-2">Range</th>
                </tr>
              </thead>
              <tbody>
                {comparisonData.map((job) => (
                  <tr key={job.jobId} className="border-b">
                    <td className="p-2 font-medium">{job.jobName}</td>
                    <td className="p-2 text-right">{job.count}</td>
                    <td className="p-2 text-right">{job.mean.toFixed(2)}</td>
                    <td className="p-2 text-right">{job.median.toFixed(2)}</td>
                    <td className="p-2 text-right">
                      <Badge variant={job.jobId === bestJob?.jobId ? "default" : "secondary"}>
                        {job.best_score.toFixed(2)}
                      </Badge>
                    </td>
                    <td className="p-2 text-right">{(job.max - job.min).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Variance Analysis */}
        {comparisonData.length > 1 && (
          <div>
            <h4 className="font-semibold mb-4">Between-Job Variance</h4>
            <div className="p-4 bg-muted rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Mean Variance</div>
                  <div className="text-xl font-bold">
                    {(
                      comparisonData.reduce((sum, j) => sum + Math.pow(j.mean - comparisonData.reduce((s, x) => s + x.mean, 0) / comparisonData.length, 2), 0) /
                      comparisonData.length
                    ).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Best Score Spread</div>
                  <div className="text-xl font-bold">
                    {(Math.max(...comparisonData.map((j) => j.best_score)) - Math.min(...comparisonData.map((j) => j.best_score))).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
