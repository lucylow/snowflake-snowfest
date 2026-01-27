"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, ResponsiveContainer } from "recharts"

interface BindingAffinityChartProps {
  poses: Array<{ pose_id: number; score: number; rmsd: number }>
}

export function BindingAffinityChart({ poses }: BindingAffinityChartProps) {
  const chartData = poses.map((pose, idx) => ({
    name: `Pose ${idx + 1}`,
    score: Math.abs(pose.score),
    rmsd: pose.rmsd,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Binding Affinity Distribution</CardTitle>
        <CardDescription>Energy scores across all generated poses (lower is better)</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            score: {
              label: "Binding Score (kcal/mol)",
              color: "hsl(var(--chart-1))",
            },
          }}
          className="h-[300px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="score" fill="var(--color-score)" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
