"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart3, TrendingDown, TrendingUp, Minus, AlertTriangle } from "lucide-react"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, XAxis, YAxis, ResponsiveContainer, LineChart, Line, BoxPlot, Cell } from "recharts"

interface StatisticalAnalysisProps {
  dockingResults: {
    results?: Array<{
      ligand_name: string
      modes?: Array<{
        affinity: number
        rmsd_lb?: number
        rmsd_ub?: number
      }>
    }>
    best_score?: number
  } | {
    poses?: Array<{
      score: number
      rmsd: number
    }>
    best_pose?: {
      score: number
    }
  }
}

export function StatisticalAnalysis({ dockingResults }: StatisticalAnalysisProps) {
  // Extract all binding affinities
  const allAffinities: number[] = []
  const ligandStats: Array<{ name: string; best: number; mean: number; count: number }> = []

  // Handle different data formats
  if ('poses' in dockingResults && dockingResults.poses) {
    // Format from DockingResult interface
    dockingResults.poses.forEach((pose, idx) => {
      if (pose.score !== undefined) {
        allAffinities.push(pose.score)
        ligandStats.push({
          name: `Pose ${idx + 1}`,
          best: pose.score,
          mean: pose.score,
          count: 1,
        })
      }
    })
  } else if ('results' in dockingResults && dockingResults.results) {
    // Format from docking service
    dockingResults.results.forEach((result) => {
      const modes = result.modes || []
      const affinities = modes.map((m) => m.affinity).filter((a): a is number => a !== undefined)
      
      if (affinities.length > 0) {
        allAffinities.push(...affinities)
        ligandStats.push({
          name: result.ligand_name,
          best: Math.min(...affinities),
          mean: affinities.reduce((a, b) => a + b, 0) / affinities.length,
          count: affinities.length,
        })
      }
    })
  }

  if (allAffinities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Statistical Analysis</CardTitle>
          <CardDescription>No data available for analysis</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  // Calculate statistics
  const sorted = [...allAffinities].sort((a, b) => a - b)
  const mean = allAffinities.reduce((a, b) => a + b, 0) / allAffinities.length
  const median = sorted[Math.floor(sorted.length / 2)]
  const variance = allAffinities.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / allAffinities.length
  const stdDev = Math.sqrt(variance)
  const min = Math.min(...allAffinities)
  const max = Math.max(...allAffinities)
  const q1 = sorted[Math.floor(sorted.length * 0.25)]
  const q3 = sorted[Math.floor(sorted.length * 0.75)]
  const iqr = q3 - q1
  const lowerBound = q1 - 1.5 * iqr
  const upperBound = q3 + 1.5 * iqr
  const outliers = allAffinities.filter((v) => v < lowerBound || v > upperBound)

  // Create histogram data
  const bins = 15
  const binWidth = (max - min) / bins
  const histogramData = Array.from({ length: bins }, (_, i) => {
    const binStart = min + i * binWidth
    const binEnd = min + (i + 1) * binWidth
    const count = allAffinities.filter((v) => v >= binStart && v < binEnd).length
    return {
      bin: `${binStart.toFixed(1)} to ${binEnd.toFixed(1)}`,
      count,
      frequency: count / allAffinities.length,
    }
  })

  // Box plot data
  const boxPlotData = [
    {
      name: "Binding Affinity",
      min,
      q1,
      median,
      q3,
      max,
      outliers: outliers.length,
    },
  ]

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Statistical Analysis
          </CardTitle>
          <CardDescription>Comprehensive statistical analysis of docking results</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Summary Statistics */}
          <div>
            <h4 className="font-semibold mb-4">Summary Statistics</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-xs text-muted-foreground mb-1">Count</div>
                <div className="text-2xl font-bold">{allAffinities.length}</div>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-xs text-muted-foreground mb-1">Mean</div>
                <div className="text-2xl font-bold">{mean.toFixed(2)}</div>
                <div className="text-xs text-muted-foreground">kcal/mol</div>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-xs text-muted-foreground mb-1">Median</div>
                <div className="text-2xl font-bold">{median.toFixed(2)}</div>
                <div className="text-xs text-muted-foreground">kcal/mol</div>
              </div>
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-xs text-muted-foreground mb-1">Std Dev</div>
                <div className="text-2xl font-bold">{stdDev.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* Distribution Metrics */}
          <div>
            <h4 className="font-semibold mb-4">Distribution Metrics</h4>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xs text-muted-foreground">Min</div>
                <div className="font-semibold">{min.toFixed(2)}</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xs text-muted-foreground">Q1</div>
                <div className="font-semibold">{q1.toFixed(2)}</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xs text-muted-foreground">Q2 (Median)</div>
                <div className="font-semibold">{median.toFixed(2)}</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xs text-muted-foreground">Q3</div>
                <div className="font-semibold">{q3.toFixed(2)}</div>
              </div>
              <div className="p-2 bg-muted/50 rounded">
                <div className="text-xs text-muted-foreground">Max</div>
                <div className="font-semibold">{max.toFixed(2)}</div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Minus className="w-4 h-4" />
                <span>Range: {(max - min).toFixed(2)}</span>
              </div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                <span>IQR: {iqr.toFixed(2)}</span>
              </div>
              {outliers.length > 0 && (
                <div className="flex items-center gap-2 text-orange-600">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Outliers: {outliers.length} ({(outliers.length / allAffinities.length * 100).toFixed(1)}%)</span>
                </div>
              )}
            </div>
          </div>

          {/* Histogram */}
          <div>
            <h4 className="font-semibold mb-4">Distribution Histogram</h4>
            <ChartContainer
              config={{
                count: {
                  label: "Frequency",
                  color: "hsl(var(--chart-1))",
                },
              }}
              className="h-[300px]"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={histogramData}>
                  <XAxis dataKey="bin" angle={-45} textAnchor="end" height={80} fontSize={10} />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="count" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartContainer>
          </div>

          {/* Ligand Comparison */}
          {ligandStats.length > 1 && (
            <div>
              <h4 className="font-semibold mb-4">Ligand Comparison</h4>
              <ChartContainer
                config={{
                  best: {
                    label: "Best Score",
                    color: "hsl(var(--chart-2))",
                  },
                  mean: {
                    label: "Mean Score",
                    color: "hsl(var(--chart-3))",
                  },
                }}
                className="h-[300px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ligandStats.slice(0, 10)}>
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} fontSize={10} />
                    <YAxis />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="best" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="mean" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
